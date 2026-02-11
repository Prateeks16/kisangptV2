import asyncio
from sentence_transformers import CrossEncoder

# Load the Multilingual Cross-Encoder
# This model is excellent for multilingual reranking (supports Hindi, English, etc.)
MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

print(f"Loading Reranker Model: {MODEL_NAME}...")
# We load it globally so it stays in memory
reranker = CrossEncoder(MODEL_NAME, max_length=512)

async def rerank_documents(query: str, docs: list, top_k: int = 5) -> list:
    """
    Takes a large list of documents (e.g., 20) and returns the top_k (e.g., 5)
    most relevant ones using a Cross-Encoder.
    """
    if not docs:
        return []

    # 1. Prepare pairs: [[Query, Doc1], [Query, Doc2], ...]
    # The Cross-Encoder needs to see both at the same time to judge relevance.
    pairs = []
    for doc in docs:
        # Extract the text content from the Qdrant payload
        doc_text = doc.payload.get("text") or doc.payload.get("chunk") or ""
        pairs.append([query, doc_text])

    # 2. Score the pairs
    # This is CPU-intensive, so we run it in a separate thread to keep the API fast
    loop = asyncio.get_running_loop()
    scores = await loop.run_in_executor(None, reranker.predict, pairs)

    # 3. Attach scores and Sort
    scored_docs = []
    for doc, score in zip(docs, scores):
        # We add the score to the payload so we can see it in the API response (debugging)
        doc.payload["rerank_score"] = float(score)
        scored_docs.append(doc)

    # Sort descending (Highest score first)
    scored_docs.sort(key=lambda x: x.payload["rerank_score"], reverse=True)

    # 4. Return the top K
    return scored_docs[:top_k]