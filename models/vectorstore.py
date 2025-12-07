import os
import time
import logging
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from app.config import PINECONE_API_KEY, VECTOR_COLLECTION_NAME

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize the Pinecone Client once
_pc = Pinecone(api_key=PINECONE_API_KEY)

def get_index(index_name: str = VECTOR_COLLECTION_NAME):
    """
    Returns the Pinecone Index. Creates it if it doesn't exist.
    """
    # Check if index exists
    existing_indexes = [i.name for i in _pc.list_indexes()]
    
    if index_name not in existing_indexes:
        logger.info(f"Creating new Pinecone index: {index_name}")
        try:
            _pc.create_index(
                name=index_name,
                dimension=768, # Matches 'all-mpnet-base-v2' dimension
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1" # Default region, change if needed
                )
            )
            # Wait a moment for initialization
            time.sleep(10)
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            raise e

    return _pc.Index(index_name)

def upsert_batch(
    collection_name: str, # In Pinecone, this maps to the Index Name
    ids: List[str],
    embeddings: List[List[float]],
    metadatas: Optional[List[Dict[str, Any]]] = None,
    documents: Optional[List[str]] = None
):
    """
    Upserts vectors into Pinecone.
    """
    index = get_index(collection_name)
    
    # Prepare data for Pinecone (needs list of dicts/tuples)
    vectors_to_upsert = []
    
    for i, _id in enumerate(ids):
        # 1. Merge document text into metadata if provided
        meta = metadatas[i] if metadatas else {}
        if documents and i < len(documents):
            meta["text_content"] = documents[i]
            
        # 2. Add to batch
        vectors_to_upsert.append({
            "id": _id,
            "values": embeddings[i],
            "metadata": meta
        })

    # 3. Upsert
    try:
        # Upsert in batches of 100 to be safe
        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i : i + batch_size]
            index.upsert(vectors=batch)
            
        logger.info(f"Successfully upserted {len(vectors_to_upsert)} vectors to Pinecone.")
    except Exception as e:
        logger.error(f"Pinecone Upsert Error: {e}")
        raise e

def search(
    collection_name: str,
    query_embeddings: List[List[float]],
    n_results: int = 5
) -> Dict[str, Any]:
    """
    Runs search and reformats result to match ChromaDB structure 
    so the rest of your app doesn't break.
    """
    index = get_index(collection_name)
    
    # Chroma structure placeholders
    all_ids = []
    all_metadatas = []
    all_distances = []
    
    # Pinecone queries usually take one vector at a time. 
    # We loop to support the list-of-lists signature.
    for emb in query_embeddings:
        try:
            results = index.query(
                vector=emb,
                top_k=n_results,
                include_metadata=True
            )
            
            # Extract data for this single query
            current_ids = [match['id'] for match in results['matches']]
            current_metas = [match['metadata'] for match in results['matches']]
            current_scores = [match['score'] for match in results['matches']]
            
            all_ids.append(current_ids)
            all_metadatas.append(current_metas)
            all_distances.append(current_scores)
            
        except Exception as e:
            logger.error(f"Pinecone Search Error: {e}")
            return {}

    # Return structure matching ChromaDB so agents/graph.py doesn't break
    return {
        "ids": all_ids,          # List of Lists
        "metadatas": all_metadatas, # List of Lists
        "distances": all_distances
    }