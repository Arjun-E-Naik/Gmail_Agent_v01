# gmail/sync.py
import time
from gmail.oauth import gmail_authenticate
from gmail.gmail_api import list_messages, get_message
from db.firestore_client import save_email_doc
from models.embeddings import embed_text
from models.vectorstore import upsert_batch
from app.config import VECTOR_COLLECTION_NAME

def sync_new_emails(user_id: str, query: str = "", max_results: int = 500):
    """
    Syncs a large number of emails (default 500).
    """
    print(f"🔄 Authenticating for user: {user_id}...")
    service = gmail_authenticate(user_id)
    
    print(f"📥 Fetching list of up to {max_results} emails...")
    msgs = list_messages(service=service, query=query, max_results=max_results)
    print(f"✅ Found {len(msgs)} messages. Starting processing...")

    # Batch lists for vector upsert
    batch_ids = []
    batch_embeddings = []
    batch_metadatas = []
    batch_docs = []
    
    count = 0
    total = len(msgs)

    for m in msgs:
        msg_id = m['id']
        
        # 1. Fetch full email content
        doc = get_message(service=service, msg_id=msg_id)
        if not doc:
            continue

        # 2. Save to Firestore (The Source of Truth)
        save_email_doc(doc)

        # 3. Prepare for Vector Store
        body_text = doc.get("body", "") or ""
        subject = doc.get("subject", "") or ""
        text_for_embedding = f"Subject: {subject}\nFrom: {doc.get('from')}\n\n{body_text[:1000]}" # Truncate for embedding speed
        
        embedding = embed_text(text_for_embedding)

        # Add to temporary batch lists
        batch_ids.append(msg_id)
        batch_embeddings.append(embedding)
        batch_metadatas.append({
            "subject": subject,
            "from": doc.get('from', 'Unknown'),
            "date": doc.get('date', ''),
            "email_id": msg_id
        })
        batch_docs.append(text_for_embedding[:1000]) # Store snippet in Pinecone metadata

        # 4. Upsert when batch reaches 10 items (to be safe and fast)
        if len(batch_ids) >= 10:
            upsert_batch(
                collection_name=VECTOR_COLLECTION_NAME,
                ids=batch_ids,
                embeddings=batch_embeddings,
                metadatas=batch_metadatas,
                documents=batch_docs
            )
            # Clear batches
            batch_ids = []
            batch_embeddings = []
            batch_metadatas = []
            batch_docs = []
            print(f"   [Saved batch] Progress: {count}/{total}")

        count += 1
        # Gmail API rate limit protection
        time.sleep(0.1)

    # 5. Upsert any remaining items in the batch
    if batch_ids:
        upsert_batch(
            collection_name=VECTOR_COLLECTION_NAME,
            ids=batch_ids,
            embeddings=batch_embeddings,
            metadatas=batch_metadatas,
            documents=batch_docs
        )
        print(f"   [Saved final batch]")

    print(f"🎉 Sync Complete! Indexed {count} emails.")
    return count