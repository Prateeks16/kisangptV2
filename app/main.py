from fastapi import FastAPI
from app.api.v1 import chat
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# Register the Chat Router
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])

@app.get("/")
def root():
    return {
        "message": "KisanGPT Enterprise API is running",
        "docs": "http://127.0.0.1:8000/docs"
    }