import os
import time
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# 1. Load Environment Variables
load_dotenv()

API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "email-embeddings" # Must match app/config.py

print("------------ DIAGNOSTICS START ------------")

# CHECK 1: API Key
if not API_KEY:
    print("❌ ERROR: PINECONE_API_KEY is missing in .env")
    exit()
else:
    print(f"✅ Found API Key: {API_KEY[:5]}...")

try:
    # CHECK 2: Connection
    pc = Pinecone(api_key=API_KEY)
    print("✅ Connected to Pinecone Client")

    # CHECK 3: List Indexes
    indexes = pc.list_indexes()
    index_names = [i.name for i in indexes]
    print(f"🔎 Existing Indexes: {index_names}")

    if INDEX_NAME not in index_names:
        print(f"⚠️  Index '{INDEX_NAME}' does NOT exist. Attempting to create...")
        try:
            pc.create_index(
                name=INDEX_NAME,
                dimension=768,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            print("⏳ Creating index... (waiting 10s)")
            time.sleep(10)
        except Exception as e:
            print(f"❌ Failed to create index: {e}")
            exit()
    else:
        print(f"✅ Index '{INDEX_NAME}' exists.")

    # CHECK 4: Upsert Test Vector
    index = pc.Index(INDEX_NAME)
    print(f"📤 Attempting to upsert a TEST vector to '{INDEX_NAME}'...")
    
    # Dummy vector (768 dimensions of 0.1)
    test_vector = [0.1] * 768
    
    upsert_response = index.upsert(
        vectors=[{
            "id": "test_diagnostic_id",
            "values": test_vector,
            "metadata": {"subject": "Test Entry", "body": "This is a test."}
        }]
    )
    print(f"✅ Upsert Response: {upsert_response}")

    # CHECK 5: Read it back
    print("re-querying the test vector...")
    time.sleep(2) # Give it a moment to index
    fetch_res = index.fetch(ids=["test_diagnostic_id"])
    
    if fetch_res and fetch_res.vectors:
        print("🎉 SUCCESS! Vector stored and retrieved.")
        print(f"   Data: {fetch_res.vectors['test_diagnostic_id'].metadata}")
    else:
        print("❌ ERROR: Upsert appeared successful, but Fetch returned nothing.")

except Exception as e:
    print(f"❌ CRITICAL ERROR: {e}")

print("------------ DIAGNOSTICS END ------------")