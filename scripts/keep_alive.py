import os
import sys
from qdrant_client import QdrantClient

# Load secrets from Environment Variables (GitHub will provide these)
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
COLLECTION_NAME = "docs_kisangpt"  # Your actual collection name

if not QDRANT_URL or not QDRANT_API_KEY:
    print("❌ Error: Secrets not found!")
    sys.exit(1)

def ping_qdrant():
    print("💓 Sending Heartbeat to Qdrant...")
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        
        # This simple "Get Info" call counts as activity
        info = client.get_collection(COLLECTION_NAME)
        
        print(f"✅ Success! Collection '{COLLECTION_NAME}' is active.")
        print(f"   - Status: {info.status}")
        print(f"   - Vectors: {info.vectors_count}")
        
    except Exception as e:
        print(f"❌ Heartbeat Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    ping_qdrant()