"""
============================================================================
 rag_engine.py
 RAG (Retrieval-Augmented Generation) motoru.

 AKIS:
   1) Yeni gelen yorum -> TF-IDF vektorlestirme
   2) Referans veri setindeki gecmis yorumlarla Cosine Similarity hesabi
   3) En benzer ilk K (varsayilan 3) yorum + onaylanmis cevap secilir
   4) Bu K ornek, prompt icine "few-shot" baglam olarak yerlestirilir
   5) Gemini API'ye TEK istek atilir (token/maliyet tasarrufu bu adimda saglanir,
      cunku butun veri seti degil, sadece en alakali 3 ornek gonderilir)

 RATE LIMIT KORUMASI:
   Basit bir "sliding window" sayac ile dakikada GEMINI_RATE_LIMIT_RPM
   istekten fazlasi gonderilmez; limit asilirsa istek, limit acilana kadar
   bekletilir (kuyruklanir) ya da HTTP 429 donerek istemciye bildirilir.
============================================================================
"""

from __future__ import annotations

import os
import time
import logging
import threading
from collections import deque
from dataclasses import dataclass

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# NOT: Eski "google-generativeai" paketi kullanımdan kaldırılmıştır (deprecated).
# Güncel resmi SDK "google-genai" paketidir (import: `from google import genai`).
from google import genai
from google.genai import errors as genai_errors

logger = logging.getLogger("rag_engine")


# ----------------------------------------------------------------------------
# OZEL HATA SINIFLARI
# ----------------------------------------------------------------------------
class RateLimitExceededError(Exception):
    """Dakikalik istek limiti asildiginda firlatilir."""


class GeminiAPIError(Exception):
    """Gemini API ile iletisimde beklenmeyen bir hata olustugunda firlatilir."""


class EmptyDatasetError(Exception):
    """Referans veri seti bos oldugunda firlatilir."""


# ----------------------------------------------------------------------------
# RATE LIMITER (Sliding Window)
# ----------------------------------------------------------------------------
class SlidingWindowRateLimiter:
    """
    Son 60 saniye icinde yapilan istek sayisini takip eden, thread-safe
    basit bir rate limiter. Google Gemini free-tier / dusuk katman
    limitlerine (ornek: 15 RPM) uyum icin kullanilir.
    """

    def __init__(self, max_requests_per_minute: int):
        self.max_requests = max_requests_per_minute
        self.window_seconds = 60.0
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        """Yeni bir istege izin varsa True doner ve zaman damgasini kaydeder."""
        with self._lock:
            now = time.monotonic()
            # Pencere disina cikan (60 saniyeden eski) kayitlari temizle
            while self._timestamps and now - self._timestamps[0] > self.window_seconds:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.max_requests:
                return False

            self._timestamps.append(now)
            return True

    def seconds_until_next_slot(self) -> float:
        """Bir sonraki izin verilen istege kadar kac saniye kaldigini hesaplar."""
        with self._lock:
            if not self._timestamps:
                return 0.0
            oldest = self._timestamps[0]
            wait = self.window_seconds - (time.monotonic() - oldest)
            return max(0.0, wait)


# ----------------------------------------------------------------------------
# RAG ENGINE
# ----------------------------------------------------------------------------
@dataclass
class RagResult:
    ai_response: str
    references: list[dict]


class RagEngine:
    def __init__(
        self,
        dataset_path: str,
        gemini_api_key: str,
        gemini_model_name: str,
        rate_limit_rpm: int = 15,
        top_k: int = 3,
    ):
        self.dataset_path = dataset_path
        self.top_k = top_k

        self.df: pd.DataFrame = self._load_dataset(dataset_path)
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),   # unigram + bigram, kisa yorumlarda daha iyi eslesme saglar
            min_df=1,
        )
        self._fit_vectorizer()

        # Gemini API istemcisini yapilandir (google-genai SDK'si)
        if not gemini_api_key:
            logger.warning("GEMINI_API_KEY tanimli degil! API cagrilari basarisiz olacaktir.")
        self.client = genai.Client(api_key=gemini_api_key)
        self.model_name = gemini_model_name

        self.rate_limiter = SlidingWindowRateLimiter(max_requests_per_minute=rate_limit_rpm)

    # ------------------------------------------------------------------
    # VERI YUKLEME
    # ------------------------------------------------------------------
    def _load_dataset(self, path: str) -> pd.DataFrame:
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Referans veri seti bulunamadi: {path}. "
                "Once scraper.py ile veri toplayip 'Örnek Yanıt' kolonunu doldurun."
            )
        df = pd.read_csv(path)
        required_cols = {"Yorum", "Duygu", "Kategori", "Örnek Yanıt"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"Veri setinde eksik kolon(lar) var: {missing}")

        # Sadece "Örnek Yanıt"ı dolu olan (insan onayli) satirlar RAG icin kullanilir
        df = df.dropna(subset=["Yorum", "Örnek Yanıt"])
        df = df[df["Örnek Yanıt"].astype(str).str.strip() != ""]
        df = df.reset_index(drop=True)

        if df.empty:
            raise EmptyDatasetError(
                "Referans veri setinde 'Örnek Yanıt' alani dolu hicbir kayit yok. "
                "RAG motoru en az 1 ornek olmadan calisamaz."
            )
        return df

    def _fit_vectorizer(self) -> None:
        self._tfidf_matrix = self.vectorizer.fit_transform(self.df["Yorum"].astype(str).tolist())

    def reload_dataset(self) -> None:
        """Veri seti disaridan guncellendiginde (yeni onayli cevaplar eklendiginde) cagirilir."""
        self.df = self._load_dataset(self.dataset_path)
        self._fit_vectorizer()
        logger.info("Veri seti yeniden yuklendi: %d kayit.", len(self.df))

    # ------------------------------------------------------------------
    # DUYGU ANALIZI (SENTIMENT DETECTION)
    # ------------------------------------------------------------------
    def _detect_sentiment(self, review: str) -> str:
        """Yeni gelen yorumun Pozitif mi Negatif mi oldugunu hizlica LLM ile tespit eder."""
        prompt = (
            f"Aşağıdaki misafir yorumunun genel duygusunu tek bir kelime ile analiz et. "
            f"Sadece 'Pozitif', 'Negatif' veya 'Nötr' kelimelerinden birini yaz.\n\nYorum: {review}"
        )
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            ans = (getattr(response, "text", None) or "").strip().lower()
            if "pozitif" in ans:
                return "Pozitif"
            if "negatif" in ans:
                return "Negatif"
            return "Nötr"
        except Exception as e:
            logger.warning(f"Duygu analizi basarisiz oldu (varsayilan olarak Notr ataniyor): {e}")
            return "Nötr"

    # ------------------------------------------------------------------
    # RETRIEVAL (TF-IDF + Cosine Similarity)
    # ------------------------------------------------------------------
    def retrieve_similar_reviews(self, new_review: str, detected_sentiment: str = None) -> list[dict]:
        """
        Yeni yorumu TF-IDF uzayina projekte eder ve cosine similarity hesaplar.
        Eger detected_sentiment verilirse, sadece o duyguya sahip olanlari onceliklendirir/filtreler.
        """
        if not new_review or not new_review.strip():
            raise ValueError("Yorum metni bos olamaz.")

        query_vector = self.vectorizer.transform([new_review])
        similarities = cosine_similarity(query_vector, self._tfidf_matrix).flatten()
        
        # Benzerlik sirasina gore tum indeksleri al
        sorted_indices = similarities.argsort()[::-1]

        results = []
        for idx in sorted_indices:
            row = self.df.iloc[idx]
            db_sentiment = str(row.get("Duygu", "")).strip().lower()
            
            # Eger duygu tespiti yapildiysa ve uymuyorsa atla (katı filtreleme)
            # Notr ise her seye izin ver.
            if detected_sentiment and detected_sentiment != "Nötr":
                if db_sentiment and detected_sentiment.lower() not in db_sentiment:
                    continue

            score = float(similarities[idx])
            results.append({
                "yorum": row["Yorum"],
                "duygu": row.get("Duygu", ""),
                "kategori": row.get("Kategori", ""),
                "ornek_yanit": row["Örnek Yanıt"],
                "benzerlik_skoru": round(score, 4),
            })
            
            if len(results) >= self.top_k:
                break
                
        # Eger filtreleme sonucu hicbir sey bulunamazsa (ornegin yeni veri setinde hic negatif yoksa)
        # Filtreyi kaldirip en benzerleri dondur (fallback mekanizmasi)
        if not results:
            logger.warning(f"'{detected_sentiment}' duygusunda referans bulunamadi, filtre kaldiriliyor.")
            for idx in sorted_indices[:self.top_k]:
                score = float(similarities[idx])
                row = self.df.iloc[idx]
                results.append({
                    "yorum": row["Yorum"],
                    "duygu": row.get("Duygu", ""),
                    "kategori": row.get("Kategori", ""),
                    "ornek_yanit": row["Örnek Yanıt"],
                    "benzerlik_skoru": round(score, 4),
                })
                
        return results

    # ------------------------------------------------------------------
    # PROMPT OLUSTURMA
    # ------------------------------------------------------------------
    @staticmethod
    def _build_prompt(new_review: str, references: list[dict], guest_name: str = "") -> str:
        context_blocks = []
        for i, ref in enumerate(references, start=1):
            context_blocks.append(
                f"### Örnek {i} (Benzerlik: {ref['benzerlik_skoru']})\n"
                f"Misafir Yorumu: {ref['yorum']}\n"
                f"Kurumsal Cevap: {ref['ornek_yanit']}\n"
            )
        context_text = "\n".join(context_blocks)
        hitap_kurali = f"- Yanıta tam olarak '{guest_name}' diyerek başla." if guest_name.strip() else "- Yanıta 'Değerli Misafirimiz,' diye başla."

        prompt = (
            "Sen 'Asteria Family Resort Belek' otelinin profesyonel, saygın ve çözüm odaklı Kurumsal İletişim Yöneticisisin.\n"
            "Görevin, misafir yorumlarına; çok karmaşık, ağdalı, edebi veya felsefi olmayan (kitap gibi okunması zor olmayan), aksine son derece DOĞAL, YALIN, ANLAŞILIR ama bir o kadar da ELİT ve KURUMSAL bir cevap yazmaktır. Metin ne çok kısa olup geçiştirmeli, ne de çok uzun olup okuyucuyu yormalıdır (maksimum 2000 karakter).\n\n"
            "--- İLETİŞİM VİZYONUN VE ALTIN KURALLAR ---\n"
            "1. DOĞAL VE ÖZGÜN GİRİŞ: 'Tesisimizde konakladığınız için teşekkür ederiz' gibi fabrikasyon kopyala-yapıştır şablonları ASLA kullanma. Yorumun ana temasına uygun, doğal, samimi ve sadece o misafire özel hissettiren akıcı bir cümleyle başla.\n"
            "2. DİK DURUŞ (SIFIR EZİKLİK): Otelimizi asla kötüleme, 'özür dileriz', 'üzüntü duyduk', 'mağduriyet' gibi zayıf ifadeler kullanma. Şikayetleri; 'Geri bildirimlerinizi hizmet kalitemizi artırmak için çok değerli bir kaynak olarak görüyoruz' gibi dik duran, yapıcı ve elit bir dille karşıla.\n"
            "3. YALIN BÜTÜNLÜK (KARMAŞADAN UZAK): Konuları madde madde robotik listelerle cevaplama, ama aynı zamanda metni aşırı edebi, felsefi ve karmaşık bir kitaba da çevirme. Açık, net, akıcı ve sade paragraflar kullan. Personel eğitimi gibi operasyon detaylarına ASLA girme; sadece genel 'kalite standartlarımızdan' bahset.\n"
            "4. KURUMSAL DOYURUCULUK: 'İlettik, sağ olun' deyip kestirip atma. Geri bildirimlerin vizyonumuza katkısından yalın bir şekilde bahsederek metne değer kat, ama bunu yaparken süslü ve abartılı kelimelerden KESİNLİKLE uzak dur.\n"
            "5. EVRENSEL DİL VE KAPANIŞ: 'Rus, Türk, yetişkin' gibi ayrıştırıcı kelimeleri tekrarlama; 'tüm misafirlerimiz' gibi kapsayıcı ifadeler kullan. Her yoruma 'Sizi tekrar bekleriz' yazmak zorunda değilsin; yoruma uygun, doğal ve şık bir kapanış yap.\n"
            f"6. HİTAP VE İMZA: {hitap_kurali} Mutlaka cevabın en sonuna 'Asteria Family Resort Belek Yönetimi' imzasını ekle.\n\n"
            f"--- REFERANS ÖRNEKLER ---\n{context_text}\n"
            f"--- YENİ MİSAFİR YORUMU ---\n{new_review}\n\n"
            "Şimdi elit, uzun, tatmin edici ve profesyonel kurumsal cevabı yaz:"
        )
        return prompt

    # ------------------------------------------------------------------
    # GENERATION (Gemini API cagrisi + hata yonetimi + rate limit)
    # ------------------------------------------------------------------
    def generate_response(self, new_review: str, guest_name: str = "", max_retries: int = 2) -> RagResult:
        # 1) Rate limit kontrolu (Duygu analizi + Yanit uretimi icin 2 istek yapacagiz)
        if not self.rate_limiter.allow_request():
            wait_time = self.rate_limiter.seconds_until_next_slot()
            raise RateLimitExceededError(f"Limit asildi, lutfen {wait_time:.0f} saniye bekleyin.")
            
        # 2) Yeni yorumun duygusunu tespit et (Iyi/Kotu filtreleme)
        detected_sentiment = self._detect_sentiment(new_review)
        logger.info(f"Tespit edilen duygu: {detected_sentiment}")

        # 3) Retrieval adimi (Sadece ayni duygudaki referanslar getirilir)
        references = self.retrieve_similar_reviews(new_review, detected_sentiment)
        prompt = self._build_prompt(new_review, references, guest_name)

        # Tekrar rate limit kontrolu yapalim
        if not self.rate_limiter.allow_request():
            time.sleep(2) # Kucuk bir gecikme verelim
            wait_time = self.rate_limiter.seconds_until_next_slot()
            logger.warning("Rate limit asildi. %.1f saniye sonra tekrar denenmeli.", wait_time)
            raise RateLimitExceededError(
                f"API istek limiti asildi (dakikada izin verilen istek sayisi doldu). "
                f"Lutfen yaklasik {wait_time:.0f} saniye sonra tekrar deneyin."
            )

        # 3) Gemini API cagrisi (hata yonetimi + exponential backoff ile retry)
        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
                ai_text = (getattr(response, "text", None) or "").strip()
                if not ai_text:
                    raise GeminiAPIError("Gemini API bos yanit dondurdu.")
                return RagResult(ai_response=ai_text, references=references)

            except genai_errors.ClientError as exc:
                # 4xx hatalari: 429 (kota/rate limit) -> backoff ile tekrar dene,
                # 400/404 (gecersiz model adi / gecersiz istek) -> kalici hata, tekrar deneme
                status_code = getattr(exc, "status", None) or getattr(exc, "code", None)
                if status_code == 429:
                    last_error = exc
                    wait = 2 ** attempt
                    logger.warning(
                        "Gemini kota/rate-limit hatasi (deneme %d/%d). %ds bekleniyor...",
                        attempt, max_retries, wait,
                    )
                    time.sleep(wait)
                    continue

                logger.error(
                    "Gecersiz istek (muhtemelen GEMINI_MODEL_NAME hatali: '%s'): %s",
                    self.model_name, exc,
                )
                raise GeminiAPIError(
                    f"Gemini API gecersiz istek hatasi verdi (HTTP {status_code}). "
                    f"GEMINI_MODEL_NAME ('{self.model_name}') degerinin Google AI "
                    f"Studio'da gecerli bir model ID'si oldugundan emin olun. Detay: {exc}"
                ) from exc

            except genai_errors.ServerError as exc:
                # 5xx hatalari: Google tarafi gecici sorun -> backoff ile tekrar dene
                last_error = exc
                wait = 2 ** attempt
                logger.warning(
                    "Gemini sunucu hatasi (deneme %d/%d): %s. %ds bekleniyor...",
                    attempt, max_retries, exc, wait,
                )
                time.sleep(wait)

            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.exception("Beklenmeyen hata (deneme %d/%d): %s", attempt, max_retries, exc)
                break

        raise GeminiAPIError(f"Gemini API cagrisi {max_retries} denemeden sonra basarisiz oldu: {last_error}")
