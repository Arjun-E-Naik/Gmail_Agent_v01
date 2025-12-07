#!/usr/bin/env python3
"""
Project scanner CLI
- Scans a python project for syntax errors, TODOs, possible secrets, large files, and optionally runs ruff/pyright/mypy/pytest if installed.
- Writes a consolidated report to ./logs/project_report.txt
"""
from __future__ import annotations
import argparse
import os
import re
import sys
import shutil
import subprocess
import json
from pathlib import Path
import compileall
import textwrap
from datetime import datetime

# Config: ignore these by default (safe)
DEFAULT_IGNORES = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    "node_modules",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "credentials",
    "credentials.json",
    "token.json",
    ".env",
    "secrets.json",
}

SENSITIVE_FILENAME_PATTERNS = [
    re.compile(r"credentials(\.json|\.yaml|\.yml)?$", re.I),
    re.compile(r"token(\.json)?$", re.I),
    re.compile(r"\.env$", re.I),
    re.compile(r"aws.*(secret|key)", re.I),
    re.compile(r"private.*key", re.I),
]

# Basic secret-like regexes (non-exhaustive, heuristic only)
SECRET_REGEXES = {
    "AWS Access Key ID": re.compile(r"AKIA[0-9A-Z]{16}"),
    "AWS Secret Access Key": re.compile(r"(?i)aws(.{0,20})?(secret|secret_access_key|secretkey).{0,80}"),
    "Google API Key-like": re.compile(r"AIza[0-9A-Za-z-_]{35}"),
    "Generic long hex (possible token)": re.compile(r"\b[0-9a-fA-F]{32,}\b"),
    "Private key PEM header": re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----"),
}

# Where to write the report
REPORT_DIR = Path("logs")
REPORT_FILE = REPORT_DIR / "project_report.txt"


def run_subprocess(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"Tool not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", "Timed out"


def check_tool_available(tool: str) -> bool:
    return shutil.which(tool) is not None


def find_files(root: Path, exts: set[str], ignore: set[str]) -> list[Path]:
    files = []
    for p in root.rglob("*"):
        if any(part in ignore for part in p.parts):
            continue
        if p.is_file() and (p.suffix in exts or True):  # we will filter for content later
            files.append(p)
    return files


def scan_syntax(root: Path, ignore: set[str]) -> dict:
    """Use compileall to detect syntax errors quickly."""
    summary = {"compiled": 0, "failures": []}
    # compileall works with file paths; exclude ignored dirs by temporarily filtering
    for pyfile in root.rglob("*.py"):
        if any(part in ignore for part in pyfile.parts):
            continue
        try:
            # compile the file
            compiled = compile(pyfile.read_text(encoding="utf-8", errors="ignore"), str(pyfile), "exec")
            summary["compiled"] += 1
        except Exception as e:
            summary["failures"].append({"file": str(pyfile), "error": repr(e)})
    return summary


def scan_todos(root: Path, ignore: set[str]) -> list[dict]:
    todos = []
    todo_re = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.I)
    for f in root.rglob("*"):
        if f.is_file() and any(part in ignore for part in f.parts):
            continue
        if f.is_file() and f.suffix in {".py", ".md", ".rst", ".txt", ".js", ".ts"}:
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                if todo_re.search(line):
                    todos.append({"file": str(f), "line": i, "text": line.strip()})
    return todos


def scan_for_secrets(root: Path, ignore: set[str]) -> list[dict]:
    findings = []
    # check filenames for sensitive patterns
    for p in root.rglob("*"):
        if any(part in ignore for part in p.parts):
            continue
        name = p.name
        for pat in SENSITIVE_FILENAME_PATTERNS:
            if pat.search(name):
                findings.append({"type": "sensitive_filename", "file": str(p), "matched": name})
    # check content heuristics
    for p in root.rglob("*"):
        if p.is_file() and any(part in ignore for part in p.parts):
            continue
        if p.suffix in {".py", ".env", ".json", ".yaml", ".yml", ".txt", ".cfg", ".ini", ".md"}:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for label, rex in SECRET_REGEXES.items():
                if rex.search(text):
                    findings.append({"type": "secret_pattern", "file": str(p), "pattern": label})
    return findings


def find_large_files(root: Path, ignore: set[str], size_mb: int = 5) -> list[dict]:
    big = []
    for p in root.rglob("*"):
        if p.is_file() and not any(part in ignore for part in p.parts):
            try:
                sz = p.stat().st_size
            except Exception:
                continue
            if sz >= size_mb * 1024 * 1024:
                big.append({"file": str(p), "size_mb": round(sz / (1024 * 1024), 2)})
    return sorted(big, key=lambda x: -x["size_mb"])


def run_linters(root: Path, tools: list[str], ignore: set[str]) -> dict:
    results = {}
    for t in tools:
        if not check_tool_available(t):
            results[t] = {"available": False, "rc": None, "out": "", "err": f"{t} not found"}
            continue
        if t == "ruff":
            cmd = [t, "check", str(root), "--select", "E,F,W", "--quiet"]
        elif t == "pyright":
            cmd = [t, str(root)]
        elif t == "mypy":
            cmd = [t, str(root)]
        elif t == "pytest":
            cmd = [t, str(root)]
        else:
            cmd = [t, str(root)]
        rc, out, err = run_subprocess(cmd, cwd=root, timeout=120)
        results[t] = {"available": True, "rc": rc, "out": out, "err": err}
    return results


def write_report(report_path: Path, content: str):
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(content, encoding="utf-8")
    print(f"Report written to {report_path}")


def generate_report(root: Path, ignore: set[str], run_tools: bool):
    now = datetime.utcnow().isoformat() + "Z"
    header = f"Project Scan Report\nPath: {root}\nGenerated: {now}\n\n"
    parts = [header]

    # 1) Basic repo stats
    py_files = list(root.rglob("*.py"))
    parts.append(f"Python files count: {len(py_files)}\n")

    # 2) Syntax check
    parts.append("== Syntax / Compile checks ==\n")
    syntax = scan_syntax(root, ignore)
    parts.append(f"Compiled files: {syntax['compiled']}\n")
    if syntax["failures"]:
        parts.append("Failures:\n")
        for f in syntax["failures"]:
            parts.append(f" - {f['file']}: {f['error']}\n")
    else:
        parts.append("No syntax errors found.\n")

    # 3) TODOs
    parts.append("\n== TODO / FIXME / HACK markers ==\n")
    todos = scan_todos(root, ignore)
    if todos:
        for t in todos[:200]:
            parts.append(f" - {t['file']}:{t['line']} -> {t['text']}\n")
        if len(todos) > 200:
            parts.append(f" (And {len(todos)-200} more...)\n")
    else:
        parts.append("No TODO-like markers found.\n")

    # 4) Secrets / Sensitive names
    parts.append("\n== Sensitive filename / token heuristics ==\n")
    secrets = scan_for_secrets(root, ignore)
    if secrets:
        for s in secrets:
            parts.append(f" - {s['type']}: {s['file']} ({s.get('pattern') or s.get('matched')})\n")
    else:
        parts.append("No obvious sensitive filenames or token patterns found (heuristic scan).\n")

    # 5) Large files
    parts.append("\n== Large files (>= 5MB) ==\n")
    big = find_large_files(root, ignore)
    if big:
        for b in big[:100]:
            parts.append(f" - {b['file']} : {b['size_mb']} MB\n")
    else:
        parts.append("No large files found.\n")

    # 6) External tools (ruff / pyright / mypy / pytest) if requested
    if run_tools:
        parts.append("\n== External tools output ==\n")
        tools = ["ruff", "pyright", "mypy", "pytest"]
        lint_results = run_linters(root, tools, ignore)
        for t, res in lint_results.items():
            parts.append(f"\n--- {t} ---\n")
            if not res.get("available", False):
                parts.append(f"Tool not available: {res.get('err')}\n")
            else:
                parts.append(f"Return code: {res.get('rc')}\n")
                if res.get("out"):
                    parts.append("STDOUT:\n")
                    parts.append(res["out"] + "\n")
                if res.get("err"):
                    parts.append("STDERR:\n")
                    parts.append(res["err"] + "\n")
    else:
        parts.append("\n(External tools not run. Use --run-tools to run ruff/pyright/mypy/pytest if installed.)\n")

    # 7) Helpful hints
    parts.append("\n== Hints & Next Steps ==\n")
    parts.append(textwrap.dedent("""
    - If secrets were found, remove them and rotate keys immediately.
    - Run `python -m pip install ruff pyright mypy pytest` and re-run with --run-tools for richer results.
    - Use `.gitignore` to avoid committing credentials; consider adding a pre-commit hook.
    - For Gmail projects specifically: check credentials/ and .env for OAuth files and never commit them.
    """))

    content = "\n".join(parts)
    write_report(REPORT_FILE, content)


def main():
    parser = argparse.ArgumentParser(description="Scan a project folder for issues and generate a report.")
    parser.add_argument("--path", "-p", type=str, default=".", help="Path to project root (default: current dir)")
    parser.add_argument("--run-tools", action="store_true",
                        help="Run external tools if installed (ruff, pyright, mypy, pytest).")
    parser.add_argument("--include", "-i", nargs="*", default=[], help="Additional filenames/dirs to NOT ignore.")
    parser.add_argument("--ignore", "-x", nargs="*", default=[], help="Extra directories/files to ignore.")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        print("Path does not exist:", root)
        sys.exit(2)

    ignore = set(DEFAULT_IGNORES)
    ignore.update(args.ignore)
    # If users specifically include something, remove from ignore
    for inc in args.include:
        ignore.discard(inc)

    print(f"Scanning {root} ... (report will be at {REPORT_FILE})")
    generate_report(root, ignore, run_tools=args.run_tools)


if __name__ == "__main__":
    main()
