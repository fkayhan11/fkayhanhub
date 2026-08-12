import os
import re
import csv

# 1. İzole çalışma alanı yollarının belirlenmesi
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "outputs")
DATA_FILE = os.path.join(WORKSPACE_DIR, "yorumlar.txt")

# Çıktı klasörünü oluştur
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 2. Eğer klasörde hazır veri yoksa 500 adet veri oluştur (Hata vermemesi için)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        for i in range(1, 501):
            if i % 3 == 0:
                f.write("Harika bir deneyimdi!   Personel çok ilgiliydi... Herkese tavsiye ederim!!\n")
            elif i % 3 == 1:
                f.write("Berbat bir yer. Yemekler soğuktu, odalar pislik içinde.,,\n")
            else:
                f.write("Fena değildi, idare eder.  Daha iyi olabilirdi ama fiyat/performans normal.\n")

# 3. Veri Temizleme Fonksiyonu
def clean_text(text):
    # Gereksiz noktalama işaretlerini temizle
    text = re.sub(r'[^\w\s]', '', text)
    # Fazla boşlukları tek boşluğa indir ve sağ/sol boşlukları kırp
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# 4. Duygu Analizi ve Anahtar Kelime Çıkarımı
def analyze_sentiment(text):
    positive_words = ['harika', 'iyi', 'güzel', 'tavsiye', 'ilgili', 'süper', 'başarılı']
    negative_words = ['berbat', 'kötü', 'soğuk', 'pis', 'rezalet', 'iğrenç', 'kaba']
    
    pos_count = sum(1 for word in positive_words if word in text.lower())
    neg_count = sum(1 for word in negative_words if word in text.lower())
    
    if pos_count > neg_count:
        return "Pozitif"
    elif neg_count > pos_count:
        return "Negatif"
    else:
        return "Nötr"

def extract_keywords(text):
    stop_words = ['bir', 've', 'ile', 'çok', 'ama', 'da', 'de', 'için', 'bu']
    words = text.lower().split()
    # Çok kısa kelimeleri ve bağlaçları filtrele
    keywords = [w for w in words if w not in stop_words and len(w) > 3]
    return ", ".join(keywords[:3])

# 5. Analizi Çalıştır
results = []
with open(DATA_FILE, "r", encoding="utf-8") as f:
    for line in f:
        original = line.strip()
        if not original:
            continue
        cleaned = clean_text(original)
        sentiment = analyze_sentiment(cleaned)
        keywords = extract_keywords(cleaned)
        results.append([cleaned, sentiment, keywords])

# 6. Sonuçları TSV dosyasına kaydet
output_file = os.path.join(OUTPUT_DIR, "analiz_sonuclari.tsv")
with open(output_file, "w", encoding="utf-8", newline='') as f:
    writer = csv.writer(f, delimiter='\t')
    writer.writerow(["Temizlenmis_Yorum", "Duygu_Durumu", "Anahtar_Kelimeler"])
    writer.writerows(results)

print("İşlem başarıyla tamamlandı. Terminale görsel tablo basılmadı.")
print(f"Toplam {len(results)} yorum analiz edilip TSV dosyasına aktarıldı.")
