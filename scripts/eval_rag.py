import sys
import os
import asyncio
import json
import time
import random
import pandas as pd
from google import genai
from qdrant_client import QdrantClient

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services import rag_service, rerank_service
from app.core.config import settings

# Initialize Judge
client = genai.Client(api_key=settings.GEMINI_API_KEY)

TEST_DATASET = [
    {"question": "What is the recommended fertilizer dose for wheat?", "expected_topic": "NPK values", "type": "PDF_Fact"},
    {"question": "What is the market price of Chilli in Guntur?", "expected_topic": "Price/Rupees", "type": "KCC_Data"},
    {"question": "How to control yellow rust in wheat?", "expected_topic": "Propiconazole", "type": "PDF_Fact"},
    {"question": "Medicine for stem borer in maize?", "expected_topic": "Pesticide name", "type": "KCC_Data"},
    {"question": "Tell me about fish pond preparation in Assam.", "expected_topic": "Liming/pH", "type": "PDF_Fact"}
]

async def llm_judge_with_retry(query, answer, context):
    prompt = f"""
    You are an impartial judge evaluating an AI Agricultural Assistant.
    USER QUERY: {query}
    RETRIEVED CONTEXT: {context[:4000]}...
    AI ANSWER: {answer}
    
    Task 1: Faithfulness (0 or 1). 1 = Answer derived from Context. 0 = Hallucination.
    Task 2: Relevance (1 to 5). 5 = Perfect. 1 = Irrelevant.
    
    Return JSON: {{"faithfulness": 0 or 1, "relevance": 1, "reason": "short explanation"}}
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = await client.aio.models.generate_content(
                model='gemini-2.5-flash', 
                contents=prompt, 
                config={'response_mime_type': 'application/json'}
            )
            return json.loads(res.text)
        except Exception as e:
            if "429" in str(e):
                wait_time = 30 + (attempt * 10) # Wait 30s, then 40s, then 50s
                print(f"      ⚠️ Quota hit. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                return {"faithfulness": 0, "relevance": 0, "reason": f"Error: {str(e)[:50]}"}
    
    return {"faithfulness": 0, "relevance": 0, "reason": "Failed after retries"}

async def run_evaluation():
    print("👨‍⚖️ Starting RAG Evaluation (Bulletproof Mode)...")
    results = []

    for item in TEST_DATASET:
        q = item["question"]
        print(f"\n📝 Testing: {q}")
        
        try:
            # 1. Run RAG Pipeline
            q_vec = await rag_service.get_embedding(q)
            docs = await rag_service.search_vector_db(q_vec, "docs_kisangpt", top_k=10)
            best_docs = await rerank_service.rerank_documents(q, docs, top_k=5)
            prompt = rag_service.format_rag_prompt(q, best_docs, None, "en") 
            answer = await rag_service.generate_answer(prompt)
            
            # 2. Judge the Result (With Retry)
            context_text = "\n".join([d.payload['text'] for d in best_docs])
            score = await llm_judge_with_retry(q, answer, context_text)
            
            print(f"   -> Faithfulness: {score['faithfulness']} | Relevance: {score['relevance']}/5")
            print(f"   -> Reason: {score['reason']}")
            
            results.append({
                "Query": q,
                "Type": item["type"],
                "Faithfulness": score['faithfulness'],
                "Relevance": score['relevance'],
                "Reason": score['reason']
            })
            
            # Safety sleep between questions
            print("   ⏳ Cooling down for 15s...")
            time.sleep(15)

        except Exception as e:
            print(f"❌ Pipeline Failed: {e}")

    # 3. Generate Report Card
    if results:
        df = pd.DataFrame(results)
        print("\n" + "="*40)
        print("📊 FINAL REPORT CARD")
        print("="*40)
        print(df[['Query', 'Faithfulness', 'Relevance']])
        df.to_csv("rag_evaluation_report.csv", index=False)
        print("✅ Report saved.")

if __name__ == "__main__":
    asyncio.run(run_evaluation())