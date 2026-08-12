import os
import time
import json
import logging
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("generator")

# Ayarları yükle
load_dotenv(".env")
api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-3.5-flash")

client = genai.Client(api_key=api_key)

input_file = "/Users/furkanmacbook/Desktop/Excel/review_analysis_workspace/yorumlar.txt"
output_file = "data/yorumlar_referans_yeni.csv"

# Eğer önceden üretilmiş veri varsa, onu yükleyip kaldığı yerden devam edelim
if os.path.exists(output_file):
    df_existing = pd.read_csv(output_file)
    processed_count = len(df_existing)
    results = df_existing.to_dict("records")
else:
    processed_count = 0
    results = []

with open(input_file, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

target_count = 300
lines = lines[:target_count]

try:
    with open("data/few_shot.txt", "r", encoding="utf-8") as f:
        few_shot_context = f.read()[:8000]
except:
    few_shot_context = ""

logger.info(f"Hedef yorum sayısı: {len(lines)}. Kaldığı yer: {processed_count}")

prompt_template = """Sen kurumsal bir otel misafir ilişkileri müdürüsün.
Aşağıdaki misafir yorumunu analiz et ve bana kesinlikle SADECE ve SADECE aşağıdaki yapıda bir JSON ver. Başka hiçbir açıklama yazma.

LÜTFEN ŞU GERÇEK OTEL CEVAPLARININ ÜSLUBUNU DİKKATLİCE İNCELE VE CEVAP ÜRETİRKEN TAM OLARAK BU KURUMSAL DİLİ KULLAN (Kapanışlara otelin ismini yaz vs):
[FEW_SHOT_CONTEXT]

Yorum: "{review}"

Beklenen JSON Formatı:
{{
  "Duygu": "Pozitif veya Negatif",
  "Kategori": "Yemek, Temizlik, Personel veya Genel",
  "Örnek Yanıt": "Sayın misafirimiz..., geri bildiriminiz için teşekkür ederiz... gibi detaylı, profesyonel kurumsal bir yanıt. Mutlaka cevabın en sonuna 'Asteria Family Resort Belek Yönetimi' imzasını ekle."
}}
"""

requests_this_minute = 0
minute_start_time = time.time()

for i in range(processed_count, len(lines)):
    if len(results) >= 300:
        logger.info("300 kayida ulasildi, uretim durduruluyor.")
        break
        
    review = lines[i]
    
    # Rate Limit (15 RPM)
    now = time.time()
    if now - minute_start_time >= 60:
        minute_start_time = now
        requests_this_minute = 0
        
    if requests_this_minute >= 14:
        sleep_time = 60 - (now - minute_start_time) + 2
        logger.info(f"Kota sinirine yaklasildi (14 istek). {sleep_time:.1f} saniye bekleniyor...")
        time.sleep(sleep_time)
        minute_start_time = time.time()
        requests_this_minute = 0

    success = False
    for attempt in range(3):
        try:
            prompt = prompt_template.format(review=review).replace("[FEW_SHOT_CONTEXT]", few_shot_context)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            requests_this_minute += 1
            
            text = (getattr(response, "text", None) or "").strip()
            # Markdown JSON bloklarini temizle
            if text.startswith("```json"):
                text = text.replace("```json", "", 1)
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            data = json.loads(text)
            
            results.append({
                "Yorum": review,
                "Duygu": data.get("Duygu", "Nötr"),
                "Kategori": data.get("Kategori", "Genel"),
                "Örnek Yanıt": data.get("Örnek Yanıt", "")
            })
            
            logger.info(f"[{i+1}/{len(lines)}] Basariyla islendi -> Duygu: {data.get('Duygu')}")
            success = True
            break
            
        except genai_errors.ClientError as e:
            status_code = getattr(e, "status", None) or getattr(e, "code", None)
            if status_code == 429:
                logger.warning(f"429 KOTA HATASI. 30 sn bekleniyor (Deneme {attempt+1}/3)")
                time.sleep(30)
                continue
            logger.error(f"ClientError: {e}")
            break
            
        except Exception as e:
            logger.warning(f"Hata (Deneme {attempt+1}/3): {e}")
            time.sleep(15)
            
    if not success:
        logger.error(f"Yorum {i+1} atlandi (Coklu hata).")
        
    # Her basarili/basarisiz istekten sonra 16K token limitini asmamak icin zorunlu bekleme
    time.sleep(15)
        
    # Her 5 kayitta bir dosyayi yedekle (checkpoint)
    if (i + 1) % 5 == 0:
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False)

# En son tamami bittiginde orijinal dosyayi degistir
df = pd.DataFrame(results)
df.to_csv("data/yorumlar_referans.csv", index=False)
logger.info("TUM ISLEMLER TAMAMLANDI! 500 adet veri data/yorumlar_referans.csv'ye yazildi.")
