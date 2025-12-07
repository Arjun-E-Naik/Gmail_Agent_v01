from sentence_transformers import SentenceTransformer
import numpy as np

# Load model once
_model = SentenceTransformer("all-mpnet-base-v2")

def embed_text(text: str) -> list:
    """
    Converts text into vector embedding (list of floats).
    """
    if not text or text.strip() == "":
        return [0.0] * 768 # all-mpnet-base-v2 has 768 dimensions

    vector = _model.encode(text, convert_to_numpy=True).astype(np.float32)
    return vector.tolist()