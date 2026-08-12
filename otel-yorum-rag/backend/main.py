"""
============================================================================
 main.py
 FastAPI Backend - RAG Tabanli Otomatik Yorum Cevaplama Sistemi

 CALISTIRMA (PyCharm terminalinde, proje kok dizininden):
    uvicorn backend.main:app --reload --port 8000

 Ardindan tarayicida frontend/index.html dosyasini acin
 (veya asagida sunulan statik dosya servisini kullanin:
  http://127.0.0.1:8000/ )
============================================================================
"""

from __future__ import annotations

import os
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.rag_engine import (
    RagEngine,
    RateLimitExceededError,
    GeminiAPIError,
    EmptyDatasetError,
)

# ----------------------------------------------------------------------------
# ORTAM DEGISKENLERI VE LOGLAMA
# ----------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-pro")
GEMINI_RATE_LIMIT_RPM = int(os.getenv("GEMINI_RATE_LIMIT_RPM", "15"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "1"))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "data", "yorumlar_referans.csv")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


# ----------------------------------------------------------------------------
# FASTAPI UYGULAMASI
# ----------------------------------------------------------------------------
app = FastAPI(
    title="Otel Yorum RAG API",
    description="Misafir yorumlarina RAG destekli otomatik yanit uretme servisi",
    version="1.0.0",
)

# CORS: frontend farkli bir origin'den (ornek: file:// veya baska port) erisebilsin diye acik birakildi.
# Uretimde bu listeyi kesinlikle gercek frontend domaininizle sinirlandirin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global RAG motoru referansi (uygulama baslarken bir kez yuklenir)
rag_engine: RagEngine | None = None


@app.on_event("startup")
def startup_event() -> None:
    """Uygulama ayaga kalkarken RAG motorunu (TF-IDF index + Gemini istemcisi) hazirlar."""
    global rag_engine
    try:
        rag_engine = RagEngine(
            dataset_path=DATASET_PATH,
            gemini_api_key=GEMINI_API_KEY,
            gemini_model_name=GEMINI_MODEL_NAME,
            rate_limit_rpm=GEMINI_RATE_LIMIT_RPM,
            top_k=RAG_TOP_K,
        )
        logger.info(
            "RAG motoru hazir. Model: %s | Veri seti: %d kayit | RPM limiti: %d",
            GEMINI_MODEL_NAME, len(rag_engine.df), GEMINI_RATE_LIMIT_RPM,
        )
    except (FileNotFoundError, ValueError, EmptyDatasetError) as exc:
        # Uygulama yine ayaga kalkar ama endpoint'ler hata dondurur; boylece
        # sadece veri seti eksikse tum servis cokmez, sorun net loglanir.
        logger.error("RAG motoru baslatilamadi: %s", exc)
        rag_engine = None


# ----------------------------------------------------------------------------
# PYDANTIC SEMALARI (Request / Response)
# ----------------------------------------------------------------------------
class YorumRequest(BaseModel):
    yorum: str = Field(..., min_length=3, max_length=4000, description="Yanitlanacak misafir yorumu")
    guest_name: str = Field(default="", description="Misafir Adi")


class ReferansYorum(BaseModel):
    yorum: str
    duygu: str
    kategori: str
    ornek_yanit: str
    benzerlik_skoru: float


class YorumResponse(BaseModel):
    ai_response: str
    references: list[ReferansYorum]
    model_used: str


class HealthResponse(BaseModel):
    status: str
    dataset_size: int | None = None
    model: str


# ----------------------------------------------------------------------------
# ENDPOINTLER
# ----------------------------------------------------------------------------
@app.get("/api/health", response_model=HealthResponse, tags=["Sistem"])
def health_check():
    """Servisin ve RAG motorunun ayakta olup olmadigini kontrol eder."""
    return HealthResponse(
        status="ready" if rag_engine is not None else "degraded_no_dataset",
        dataset_size=len(rag_engine.df) if rag_engine is not None else None,
        model=GEMINI_MODEL_NAME,
    )


@app.post("/api/generate-response", response_model=YorumResponse, tags=["RAG"])
def generate_response(payload: YorumRequest):
    """
    Ana is akisi:
      1) Gelen yorum icin TF-IDF ile en benzer 3 gecmis yorum+cevap bulunur.
      2) Bu 3 ornek, prompt'a baglam (context) olarak eklenir.
      3) Gemini API'ye tek istek atilir ve uretilen cevap donulur.
    """
    if rag_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "RAG motoru hazir degil. Referans veri seti "
                f"('{DATASET_PATH}') bulunamadi veya bos. Once scraper.py "
                "ile veri toplayip 'Örnek Yanıt' kolonunu doldurun."
            ),
        )

    try:
        result = rag_engine.generate_response(payload.yorum, payload.guest_name)
        return YorumResponse(
            ai_response=result.ai_response,
            references=[ReferansYorum(**ref) for ref in result.references],
            model_used=GEMINI_MODEL_NAME,
        )

    except RateLimitExceededError as exc:
        # 15 RPM gibi limitler asildiginda istemciye net bir 429 donulur
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    except GeminiAPIError as exc:
        logger.error("Gemini API hatasi: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    except Exception as exc:  # noqa: BLE001 - beklenmeyen her hata loglanir, 500 donulur
        logger.exception("Beklenmeyen sunucu hatasi: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Beklenmeyen bir sunucu hatasi olustu. Loglari kontrol edin.",
        ) from exc


@app.post("/api/reload-dataset", tags=["Sistem"])
def reload_dataset():
    """Veri setine yeni onayli ornekler eklendiginde (staff tarafindan) yeniden yuklemek icin."""
    if rag_engine is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="RAG motoru yuklu degil.")
    try:
        rag_engine.reload_dataset()
        return {"status": "ok", "dataset_size": len(rag_engine.df)}
    except (ValueError, EmptyDatasetError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ----------------------------------------------------------------------------
# FRONTEND STATIK DOSYA SERVISI
# ----------------------------------------------------------------------------
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")
