from google.cloud import firestore
from google.oauth2 import service_account
import os
from app.config import FIRESTORE_PROJECT, GOOGLE_CREDENTIALS, TOKENS_COLLECTIONS, EMAIL_COLLECTIONS

_db = None

def get_db():
    global _db
    if _db is None:
        # 1. Check if the specific JSON key file exists
        if GOOGLE_CREDENTIALS and os.path.exists(GOOGLE_CREDENTIALS):
            print(f"🔐 Authenticating Firestore with key: {GOOGLE_CREDENTIALS}")
            try:
                # Load credentials from the JSON file
                creds = service_account.Credentials.from_service_account_file(GOOGLE_CREDENTIALS)
                _db = firestore.Client(credentials=creds, project=FIRESTORE_PROJECT)
            except Exception as e:
                print(f"❌ Error loading credential file: {e}")
                raise e
        else:
            # 2. detailed error if file is missing
            print(f"❌ CRITICAL ERROR: Service Account Key not found at: {GOOGLE_CREDENTIALS}")
            print("Please ensure 'service_account.json' is inside the 'credentials' folder.")
            # Attempt default as a Hail Mary, but likely to fail based on your logs
            _db = firestore.Client(project=FIRESTORE_PROJECT)
            
    return _db 

def save_token_for_user(user_id: str, token_json: dict):
    db = get_db()
    doc_ref = db.collection(TOKENS_COLLECTIONS).document(user_id)
    doc_ref.set({"token": token_json})

def load_token_for_user(user_id: str):
    db = get_db()
    doc = db.collection(TOKENS_COLLECTIONS).document(user_id).get()
    if doc.exists:
        return doc.to_dict().get("token")
    return None

def save_email_doc(email_doc: dict):
    db = get_db()
    email_id = email_doc['email_id']
    db.collection(EMAIL_COLLECTIONS).document(email_id).set(email_doc)