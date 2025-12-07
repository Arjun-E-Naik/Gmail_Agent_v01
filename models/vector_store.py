import os
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load Cloud Config
CHROMA_SERVER_HOST = os.getenv("CHROMA_SERVER_HOST") # e.g., "api.trychroma.com" or your cloud tenant URL
CHROMA_SERVER_PORT = int(os.getenv("CHROMA_SERVER_PORT", "443")) # Cloud usually uses 443 (HTTPS)
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY") # Your secret token

_client: Optional[chromadb.Client] = None

def _init_client():
    global _client
    if _client is not None:
        return _client

    logger.info(f"Initializing Chroma Cloud Client at {CHROMA_SERVER_HOST}")
    
    try:
        # Configuration for Cloud/Auth
        # Note: Different providers might ask for headers differently. 
        # This is the standard Auth method for Chroma.
        
        _client = chromadb.HttpClient(
            host=CHROMA_SERVER_HOST,
            port=CHROMA_SERVER_PORT,
            ssl=True, # Cloud always uses SSL (HTTPS)
            headers={
                "X-Chroma-Token": CHROMA_API_KEY,  # Standard Header for API Key
                "Authorization": f"Bearer {CHROMA_API_KEY}" # Some providers use this instead
            }
        )
        
        # Verify connection
        _client.heartbeat()
        logger.info("Successfully connected to Chroma Cloud")
        
    except Exception as e:
        logger.error(f"Failed to connect to Chroma Cloud: {e}")
        raise e

    return _client

# ... (The rest of your functions: get_or_create_collection, upsert_batch, search remain exactly the same)


def get_or_create_collection(name: str):
    client = _init_client()
    return client.get_or_create_collection(name=name)

def upsert_batch(
    collection_name: str,
    ids: List[str],
    embeddings: List[List[float]],
    metadatas: Optional[List[Dict[str, Any]]] = None,
    documents: Optional[List[str]] = None
):
    """
    Upsert vectors. Inputs must be lists.
    """
    coll = get_or_create_collection(collection_name)
    # FIX: Argument name was 'metadatas', but you passed 'metas' in your snippet
    coll.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)

def search(
    collection_name: str,
    query_embeddings: List[List[float]],
    n_results: int = 5
) -> Dict[str, Any]:
    """
    Run similarity search. query_embeddings must be a List of Lists (e.g. [[0.1, ...]])
    """
    coll = get_or_create_collection(collection_name)
    return coll.query(query_embeddings=query_embeddings, n_results=n_results)