import asyncio
from google import genai
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from app.core.config import settings

# --- Initialization ---

# 1. Initialize Google GenAI Client
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# 2. Load Embedding Model 
print("Loading Multilingual Embedding Model...")
embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# 3. Connect to Qdrant
qclient = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY,
)

async def get_embedding(text: str) -> list[float]:
    """
    Generates vector embedding for the query.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, embedder.encode, text)

async def search_vector_db(query_vector: list[float], collection_name: str, top_k: int = 5):
    """
    Asynchronously searches Qdrant using the Universal 'query_points' method.
    This works on ALL versions of Qdrant Client.
    """
    loop = asyncio.get_running_loop()
    
    # We use query_points, which is the "raw" search method
    results = await loop.run_in_executor(
        None, 
        lambda: qclient.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True
        ).points  # Important: We extract the list of points from the response
    )
    return results

def format_rag_prompt(query: str, retrieved_docs: list, fertilizer_info: dict | None, language: str = "en") -> str:
    """
    Constructs the prompt for Gemini.
    """
    context_text = ""

    # 1. Add Structured Data (SQL Database)
    if fertilizer_info:
        context_text += f"[FERTILIZER DATABASE]\n"
        context_text += f"Crop: {fertilizer_info['crop_name']}\n"
        context_text += f"Rec. Dosage: N={fertilizer_info['n_value']} kg/ha, "
        context_text += f"P={fertilizer_info['p_value']} kg/ha, K={fertilizer_info['k_value']} kg/ha\n\n"

    # 2. Add Unstructured Data (PDFs)
    context_text += "[KNOWLEDGE BASE]\n"
    for i, doc in enumerate(retrieved_docs, 1):
        payload = doc.payload or {}
        text = payload.get("text") or payload.get("chunk") or ""
        source = payload.get("source") or payload.get("pdf") or "Unknown"
        context_text += f"Source {i}: {source}\nContent: {text}\n\n"

    # 3. Final Prompt
# Detect target language name for the prompt
    lang_map = {
        "hi": "Hindi",
        "en": "English",
        "te": "Telugu",
        "ta": "Tamil",
        "mr": "Marathi"
    }
    target_lang = lang_map.get(language, "English")

    prompt = f"""
    You are *KisanGPT*, an expert agricultural advisor for Indian farmers.
    
    CONTEXT INFORMATION:
    {context_text}
    
    USER QUERY: {query}
    
    INSTRUCTIONS:
    1. Answer primarily using the CONTEXT provided above.
    2. If [FERTILIZER DATABASE] is present, use those exact numbers.
    3. **IMPORTANT: Provide the answer entirely in {target_lang}.**
    4. Translate technical terms where appropriate, but keep N-P-K numbers in English digits (e.g., 120 kg).
    5. Keep the tone simple and helpful for a farmer.
    """
    return prompt

async def generate_answer(prompt: str) -> str:
    """
    Calls Gemini API using the new google.genai SDK.
    """
    try:
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Error connecting to AI: {str(e)}"