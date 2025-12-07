import os
from dotenv import load_dotenv

# ---------------------------------------------------------
# 1. ROBUST PATH SETUP
# Ensures we always find the .env and credentials folder
# regardless of where you run the command from.
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
CREDENTIALS_DIR = os.path.join(BASE_DIR, "credentials")

# Explicitly load the .env file
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
    print(f"✅ Configuration loaded from: {ENV_PATH}")
else:
    print(f"⚠️  WARNING: .env file NOT found at: {ENV_PATH}")

# ---------------------------------------------------------
# 2. GOOGLE & GMAIL CONFIGURATION
# ---------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly"
]

# Path to the OAuth Client ID JSON (for user login)
DEFAULT_GMAIL_CREDS = os.path.join(CREDENTIALS_DIR, "google_credentials.json")
GOOGLE_GMAIL_CREDENTIALS_PATH = os.getenv("GOOGLE_GMAIL_CREDENTIALS_PATH", DEFAULT_GMAIL_CREDS)

# Path to the Service Account JSON (for Firestore Database permission)
DEFAULT_SERVICE_ACCOUNT = os.path.join(CREDENTIALS_DIR, "service_account.json")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", DEFAULT_SERVICE_ACCOUNT)

FIRESTORE_PROJECT = os.getenv("GOOGLE_FIRESTORE_PROJECT_ID")

# ---------------------------------------------------------
# 3. PINECONE VECTOR DB CONFIGURATION
# ---------------------------------------------------------
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# Pinecone Index Name
# Best practice: use lowercase and hyphens (no underscores)
VECTOR_COLLECTION_NAME = "email-embeddings"

# ---------------------------------------------------------
# 4. FIRESTORE COLLECTION NAMES
# ---------------------------------------------------------
TOKENS_COLLECTIONS = "user_tokens"
EMAIL_COLLECTIONS = "emails"