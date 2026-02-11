import sys
import os
import glob
import json
import uuid
import asyncio
from typing import List, Dict
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from google import genai
import pypdf

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings

# --- Configuration ---
COLLECTION_NAME = "docs_kisangpt_advanced"
PDF_FOLDER = "data"

# Parent-Child Settings
PARENT_CHUNK_SIZE = 1000  # Characters (The "Context" for the LLM)
CHILD_CHUNK_SIZE = 300    # Characters (The "Searchable" snippet)
CHILD_OVERLAP = 50

# Initialize AI Clients
client_gemini = genai.Client(api_key=settings.GEMINI_API_KEY)
client_qdrant = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2") # Multilingual!

async def extract_metadata_with_ai(text_snippet: str) -> Dict:
    """
    Uses Gemini to classify the document based on its first page.
    """
    prompt = f"""
    Analyze this text from an agricultural document and extract metadata in JSON format.
    Text: "{text_snippet[:1500]}"
    
    Return ONLY valid JSON with these keys:
    - "is_state_specific": boolean
    - "state": string or null (e.g., "Assam", "Punjab")
    - "season": string or null (e.g., "Rabi", "Kharif")
    - "topic": string (e.g., "Wheat Advisory", "Pest Control")
    """
    try:
        response = await client_gemini.aio.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"⚠️ Metadata extraction failed: {e}")
        return {"is_state_specific": False, "topic": "General Agriculture"}

def create_parent_child_chunks(full_text: str) -> List[Dict]:
    """
    Splits text into Large Parents and Small Children.
    """
    chunks = []
    
    # 1. Split into Parent Chunks (Large context)
    # Simple character splitting for demo (use semantic splitting for production)
    parent_texts = [full_text[i:i+PARENT_CHUNK_SIZE] for i in range(0, len(full_text), PARENT_CHUNK_SIZE)]
    
    for parent_idx, parent_text in enumerate(parent_texts):
        # 2. Split Parent into Child Chunks (Small search units)
        # We overlap children slightly so we don't cut words in half
        child_texts = [parent_text[i:i+CHILD_CHUNK_SIZE] for i in range(0, len(parent_text), CHILD_CHUNK_SIZE - CHILD_OVERLAP)]
        
        for child_text in child_texts:
            chunks.append({
                "child_text": child_text,      # We EMBED this (Searchable)
                "parent_text": parent_text,    # We RETRIEVE this (Context for LLM)
                "parent_id": parent_idx
            })
            
    return chunks

async def ingest_data():
    print("🚀 Starting Advanced Ingestion Pipeline...")
    
    # Recreate Collection
    client_qdrant.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )

    pdf_files = glob.glob(os.path.join(PDF_FOLDER, "*.pdf"))
    print(f"📂 Found {len(pdf_files)} PDFs.")

    all_points = []
    global_id = 0

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        print(f"   📄 Processing {filename}...")
        
        # 1. Read PDF
        try:
            reader = pypdf.PdfReader(pdf_path)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
        except Exception as e:
            print(f"   ❌ Error reading {filename}: {e}")
            continue

        # 2. Extract Metadata (The "Smart" Part)
        print("      🤖 Classifying document...")
        metadata = await extract_metadata_with_ai(full_text)
        print(f"      🏷️  Tags: {metadata}")

        # 3. Parent-Child Chunking
        chunk_data = create_parent_child_chunks(full_text)
        
        # 4. Generate Embeddings (Only for Child Chunks!)
        # We embed the small text because it's precise.
        child_texts = [c["child_text"] for c in chunk_data]
        embeddings = embedder.encode(child_texts)

        # 5. Prepare Qdrant Points
        for i, data in enumerate(chunk_data):
            payload = {
                "source": filename,
                "text": data["parent_text"],  # IMPORTANT: We store the PARENT text to show the user
                "search_text": data["child_text"], # Debug info
                "metadata": metadata # Store state/season info
            }
            
            point = models.PointStruct(
                id=global_id,
                vector=embeddings[i].tolist(),
                payload=payload
            )
            all_points.append(point)
            global_id += 1

    # 6. Upload
    if all_points:
        print(f"⬆️  Uploading {len(all_points)} smart chunks to Qdrant...")
        client_qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=all_points
        )
        print("✅ Advanced Ingestion Complete!")

if __name__ == "__main__":
    asyncio.run(ingest_data())