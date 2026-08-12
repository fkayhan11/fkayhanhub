import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os

def scrape_otelpuan_reviews():
    print("Web tarayıcı başlatılıyor...")
    options = Options()
    options.add_argument('--headless')  # Tarayıcıyı arka planda gizli çalıştırır
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    url = "https://www.otelpuan.com/Asteria-Family-Resort-Belek"
    driver.get(url)
    
    print("Sayfa yükleniyor, yorumlar toplanacak (Bu işlem biraz sürebilir)...")
    
    # Sayfayı aşağı kaydırma (Infinite Scroll simülasyonu)
    last_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(10):  # Daha fazla yorum için bu sayıyı artırabilirsin
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    reviews_data = []
    
    # Otelpuan yapısına göre yorum kartlarını yakalama (Seçiciler sitenin güncel DOM yapısına göre ayarlanmalıdır)
    review_cards = driver.find_elements(By.CSS_SELECTOR, ".review-card") # Temsili CSS sınıfı
    
    for card in review_cards:
        try:
            # Yorum metnini çekme
            user_review = card.find_element(By.CSS_SELECTOR, ".review-text").text
            
            # Otel yanıtı var mı kontrol etme
            hotel_response = ""
            response_elements = card.find_elements(By.CSS_SELECTOR, ".hotel-response-text")
            if response_elements:
                hotel_response = response_elements[0].text
                
            if user_review and hotel_response:
                reviews_data.append({
                    "user_review": user_review,
                    "hotel_response": hotel_response
                })
        except Exception as e:
            continue

    driver.quit()
    
    # Verileri kaydetme
    os.makedirs('../data', exist_ok=True)
    df = pd.DataFrame(reviews_data)
    
    if not df.empty:
        df.to_csv('../data/yorumlar_referans.csv', index=False, encoding='utf-8')
        print(f"Başarılı! Toplam {len(df)} adet yorum ve yanıt eşleşmesi 'data/yorumlar_referans.csv' dosyasına kaydedildi.")
    else:
        print("Uyarı: Hiç yorum çekilemedi. HTML seçicilerini (CSS_SELECTOR) kontrol et.")

if __name__ == "__main__":
    scrape_otelpuan_reviews()