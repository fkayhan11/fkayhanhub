from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.rag_engine import generate_ai_response

app = FastAPI(title="Otel Yorum RAG Sistemi")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ReviewRequest(BaseModel):
    review_text: str

@app.post("/api/generate")
async def generate_response(request: ReviewRequest):
    ai_reply = generate_ai_response(request.review_text)
    return {"status": "success", "response": ai_reply}

# Arayüz dosyalarını sunmak için
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")