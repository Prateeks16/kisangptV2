from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import select
import time

# Internal imports
from app.models.fertilizer import Fertilizer
from app.services import rag_service, rerank_service # <--- IMPORT NEW SERVICE
from app.core.config import settings

# --- Database Setup ---
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session

router = APIRouter()

# --- Schemas ---
class ChatRequest(BaseModel):
    query: str
    language: str = "en"

class ChatResponse(BaseModel):
    answer: str
    sources: list[dict] # Changed to list[dict] to show scores
    processing_time: float

# --- Endpoint ---
@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    user_query = request.query
    
    # 1. SQL Search (Structured)
    stmt = select(Fertilizer)
    result = await db.execute(stmt)
    all_fertilizers = result.scalars().all()
    
    found_fertilizer = None
    for fert in all_fertilizers:
        if fert.crop_name.lower() in user_query.lower():
            found_fertilizer = {
                "crop_name": fert.crop_name,
                "n_value": fert.n_value,
                "p_value": fert.p_value,
                "k_value": fert.k_value
            }
            break
            
    # 2. Vector Search (Broad Retrieval)
    # We fetch 15 docs (Wide Net) instead of 4
    query_vector = await rag_service.get_embedding(user_query)
    
    initial_results = await rag_service.search_vector_db(
        query_vector, 
        collection_name="docs_kisangpt_advanced", # Use your new collection name
        top_k=15 
    )
    
    # 3. Re-ranking (Precision Filtering)
    # Filter the 15 down to the best 5
    reranked_results = await rerank_service.rerank_documents(
        query=user_query,
        docs=initial_results,
        top_k=5
    )
    
    # 4. Generate Answer with Best Docs
    prompt = rag_service.format_rag_prompt(
        query=user_query, 
        retrieved_docs=reranked_results, 
        fertilizer_info=found_fertilizer,
        language=request.language
    )
    
    bot_answer = await rag_service.generate_answer(prompt)
    
    # 5. Prepare Sources (Now with Scores!)
    source_list = []
    for hit in reranked_results:
        if hit.payload:
            source_list.append({
                "source": hit.payload.get("source", "PDF"),
                "score": hit.payload.get("rerank_score", 0.0),
                "text_preview": hit.payload.get("text", "")[:50] + "..."
            })
    
    return ChatResponse(
        answer=bot_answer,
        sources=source_list,
        processing_time=time.time() - start_time
    )