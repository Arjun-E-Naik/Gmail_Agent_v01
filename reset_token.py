# reset_token.py
from db.firestore_client import get_db

def reset():
    print("🗑️  Deleting stored token for 'dev_user'...")
    db = get_db()
    # Delete the document that stores the token
    db.collection("user_tokens").document("dev_user").delete()
    print("✅ Token deleted. You will be asked to log in again on next run.")

# if __name__ == "__main__":
#     reset()
reset()