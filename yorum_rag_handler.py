import os
import sys
import json
import time
from dotenv import load_dotenv

# Kullanıcının orijinal RAG klasörünü Python path'ine ekle
RAG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'otel-yorum-rag')
if RAG_DIR not in sys.path:
    sys.path.insert(0, RAG_DIR)

try:
    from backend.rag_engine import RagEngine, RateLimitExceededError, GeminiAPIError, EmptyDatasetError
    HAS_RAG_ENGINE = True
except ImportError:
    HAS_RAG_ENGINE = False

# Global instance for the rag engine
_rag_engine_instance = None

def get_rag_engine():
    global _rag_engine_instance
    if _rag_engine_instance is None and HAS_RAG_ENGINE:
        load_dotenv(os.path.join(RAG_DIR, '.env'))
        dataset_path = os.path.join(RAG_DIR, 'data', 'yorumlar_referans.csv')
        api_key = os.environ.get("GEMINI_API_KEY", "")
        model_name = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-pro")
        
        try:
            _rag_engine_instance = RagEngine(
                dataset_path=dataset_path,
                gemini_api_key=api_key,
                gemini_model_name=model_name,
                rate_limit_rpm=15,
                top_k=3
            )
            print("Orijinal Gemini RAG Motoru basariyla yuklendi!")
        except Exception as e:
            print(f"RAG Motoru baslatilamadi: {e}")
            
    return _rag_engine_instance

def handle_reply_request(payload):
    guest_name = payload.get('guest_name', 'Değerli Misafirimiz')
    language = payload.get('language', 'tr')
    review_text = payload.get('review_text', '').strip()
    is_retry = payload.get('retry', False)
    is_shorten = payload.get('shorten', False)
    
    if not review_text:
        return {"status": "error", "error": "Misafir yorumu boş olamaz."}
        
    engine = get_rag_engine()
    if not engine:
        return {"status": "error", "error": "Orijinal RAG Motoru (Gemini) yüklenemedi. otel-yorum-rag klasörü eksik veya hatalı."}
        
    try:
        # Eğer kullanıcı "Beğenmedim" veya "Kısalt" tuşuna bastıysa, prompt'a ek talimat koy
        modified_review = review_text
        if is_retry:
            modified_review += "\n\n(DİKKAT: Kullanıcı bir önceki ürettiğin taslağı beğenmedi. Lütfen tamamen FARKLI kelimeler kullanarak, farklı bir açıdan yaklaşan daha yaratıcı, yenilikçi ve yepyeni bir alternatif yanıt üret.)"
        elif is_shorten:
            modified_review += "\n\n(DİKKAT: Kullanıcı bir önceki ürettiğin taslağın daha kısa olmasını istiyor. Lütfen gereksiz uzatmaları atarak, doğrudan sadede gelen ama kurumsal nezaketi koruyan ÇOK DAHA KISA ve ÖZ bir yanıt üret. Cümle sayısını yarı yarıya azalt.)"
            
        # 8 saniyelik sabit bekleme süresi hesaplaması
        start_time = time.time()
        
        # Kullanıcının kendi RAG Engine'i (Few-shot, Gemini, Cosine Similarity) üzerinden yanıt üret!
        result = engine.generate_response(new_review=modified_review, guest_name=guest_name)
        
        elapsed_time = time.time() - start_time
        if elapsed_time < 8.0:
            time.sleep(8.0 - elapsed_time)
        
        # Referanslardan duygu durumunu çek
        sentiment = "Nötr"
        if result.references and len(result.references) > 0:
            sentiment = result.references[0].get("duygu", "Nötr")
        
        return {
            "status": "success",
            "reply": result.ai_response,
            "sentiment": sentiment,
            "references": [ref.get('yorum', '') for ref in result.references]
        }
    except RateLimitExceededError as e:
        return {"status": "error", "error": f"Limit Aşıldı: {str(e)}"}
    except GeminiAPIError as e:
        return {"status": "error", "error": f"Yapay Zeka Hatası: {str(e)}"}
    except Exception as e:
        return {"status": "error", "error": f"Beklenmeyen Hata: {str(e)}"}
