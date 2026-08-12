# RAG Tabanlı Otomatik Yorum Cevaplama Sistemi

Otel misafir ilişkileri ekibi için: geçmiş onaylı yanıtları referans alarak
yeni gelen yorumlara kurumsal üslupta otomatik cevap taslağı üreten sistem.

## ⚠️ Önemli Uyarılar (İlk okumanız gerekenler)

1. **Model adı:** İstekte belirtilen `"Gemini 3.5 medium"` adında resmi bir
   Google modeli bulunmuyor (Google'ın isimlendirmesi `gemini-2.5-pro`,
   `gemini-2.5-flash` vb. şeklindedir). `.env` dosyasındaki
   `GEMINI_MODEL_NAME` değerini, [Google AI Studio](https://aistudio.google.com)
   üzerinde o an erişiminiz olan güncel model ID'si ile değiştirin. Kod hiçbir
   yerde model adını sabit (hardcoded) tutmaz.
2. **Scraping yasallığı:** `scraper/scraper.py` içindeki CSS seçicileri
   **yer tutucudur**. Gerçek siteyi çalıştırmadan önce (a) sitenin
   `robots.txt` ve Kullanım Şartları'nı kontrol edin, (b) tarayıcı
   DevTools (F12) ile gerçek CSS seçicilerini bulup `SELECTORS`
   sözlüğünü güncelleyin.
3. Sistem prompt enjeksiyonuna karşı: kullanıcıdan gelen yorum metni asla
   doğrudan sistem talimatı olarak değil, her zaman "MİSAFİR YORUMU" bloğu
   içinde value olarak Gemini'ye gönderilir.

## Klasör Yapısı

```
otel-yorum-rag/
├── requirements.txt
├── .env.example              # Kopyalayıp .env yapın
├── README.md
├── scraper/
│   └── scraper.py            # Selenium ile yorum toplama
├── backend/
│   ├── __init__.py
│   ├── main.py                # FastAPI uygulaması / endpointler
│   └── rag_engine.py          # TF-IDF retrieval + Gemini generation + rate limit
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
└── data/
    └── yorumlar_referans.csv  # Örnek etiketlenmiş referans veri seti (10 kayıt)
```

## Kurulum (PyCharm Terminali)

```bash
# 1) Sanal ortam oluştur (önerilir)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 2) Bağımlılıkları kur
pip install -r requirements.txt

# 3) .env dosyasını oluştur
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
# Ardından .env içine gerçek GEMINI_API_KEY ve GEMINI_MODEL_NAME değerlerini girin
```

## Kullanım Akışı

### Adım 1 — Veri Toplama (opsiyonel, referans veri setini büyütmek için)

```bash
python scraper/scraper.py
```

Bu, `data/yorumlar_ham.csv` dosyasını üretir (sadece "Yorum" kolonu dolu).
Misafir ilişkileri ekibi bu dosyadaki her satır için `Duygu`, `Kategori` ve
**özellikle `Örnek Yanıt`** kolonlarını elle doldurup, satırları
`data/yorumlar_referans.csv` dosyasına ekler/birleştirir. RAG motoru sadece
`Örnek Yanıt` alanı dolu olan, **insan onaylı** kayıtları referans olarak
kullanır — bu, üretilen cevapların kalitesini ve kurumsal tutarlılığını
garanti eden kasıtlı bir tasarım kararıdır.

### Adım 2 — Backend'i Başlat

Proje kök dizininden:

```bash
uvicorn backend.main:app --reload --port 8000
```

Sağlık kontrolü: `http://127.0.0.1:8000/api/health`

### Adım 3 — Arayüzü Aç

Tarayıcıda şu adresi açın:

```
http://127.0.0.1:8000/
```

(Backend, `frontend/` klasörünü otomatik olarak serve eder — CORS sorunu yaşamazsınız.)

## Mimari Notlar

- **Neden TF-IDF ve neden tam bir vektör veritabanı değil?** Veri seti
  boyutu (birkaç yüz/bin yorum) için TF-IDF + cosine similarity, ek bir
  vektör veritabanı (Pinecone/Chroma) kurulumu gerektirmeden yeterli
  performansı sağlar ve harici servis bağımlılığı/maliyeti eklemez. Veri
  seti çok büyürse (>50k kayıt) `sentence-transformers` + FAISS'e
  geçilmesi önerilir.
- **Rate limit neden istemci tarafında da (frontend) değil backend'de
  uygulanıyor?** Çünkü asıl kısıt Google'ın API kotasıdır; frontend
  sadece backend'in döndürdüğü 429 hatasını kullanıcıya gösterir.
- **Neden `Örnek Yanıt` alanı boşsa satır RAG'a dahil edilmiyor?** Otomatik
  üretilen bir cevabın kendisini "örnek" olarak tekrar beslemesi (self-
  reinforcing hata döngüsü) riskini önlemek için.

## Sorun Giderme

| Belirti | Olası Neden | Çözüm |
|---|---|---|
| `503 RAG motoru hazır değil` | `data/yorumlar_referans.csv` bulunamadı/boş | Dosyanın var olduğunu ve en az 1 satırda `Örnek Yanıt` dolu olduğunu kontrol edin |
| `429 İstek limiti aşıldı` | Dakikada 15'ten fazla istek | Belirtilen süre kadar bekleyin veya `.env`'de `GEMINI_RATE_LIMIT_RPM`'i planınıza göre ayarlayın |
| `502 Bad Gateway` | Geçersiz `GEMINI_API_KEY` veya `GEMINI_MODEL_NAME` | Google AI Studio'dan geçerli değerleri doğrulayın |
| Scraper hiç yorum bulamıyor | CSS seçiciler siteyle uyuşmuyor | `scraper.py` içindeki `SELECTORS` sözlüğünü DevTools ile güncelleyin |
