"""
============================================================================
 scraper.py
 Otel yorumlarini Selenium ile toplayan veri toplama scripti.

 KULLANIM (PyCharm terminalinde):
    python scraper/scraper.py

 CIKTI:
    ../data/yorumlar_ham.csv     -> Sadece "Yorum" sutunu dolu (ham veri)
    ../data/yorumlar_ham.xlsx    -> Ayni verinin Excel versiyonu

 ONEMLI NOT (Hukuki/Etik):
    Bu script'i calistirmadan once hedef sitenin robots.txt ve
    Kullanim Sartlari'nin (ToS) otomatik veri cekmeye izin verip
    vermedigini kontrol edin. Kurumsal kullanimda genellikle site
    sahibinden yazili izin almak veya resmi bir API/partner
    entegrasyonu kullanmak en guvenli yoldur. Bu kod, istekler
    arasina bekleme (delay) koyarak ve tek bir oturumla calisarak
    sunucuya asiri yuk bindirmemeye ozen gosterir.

 SELECTOR NOTU:
    Web siteleri sik sik HTML yapisini degistirir. Asagidaki CSS
    secicileri (SELECTORS sozlugu) YER TUTUCUDUR / ORNEKTIR.
    Gercek siteyi tarayici DevTools (F12 > Elements) ile inceleyip
    kendi CSS secicilerinizi girmeniz gerekir. Kod, bu secicileri
    tek bir yerden (SELECTORS) yonetecek sekilde tasarlanmistir;
    boylece site yapisi degistiginde sadece burayi guncellersiniz.
============================================================================
"""

import os
import re
import time
import logging
from dataclasses import dataclass, field

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# ----------------------------------------------------------------------------
# LOGLAMA AYARI
# ----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scraper")


# ----------------------------------------------------------------------------
# YAPILANDIRMA
# ----------------------------------------------------------------------------
@dataclass
class ScraperConfig:
    target_url: str = "https://www.otelpuan.com/Asteria-Family-Resort-Belek"
    headless: bool = True                 # True: tarayici penceresi acilmaz (sunucu icin ideal)
    scroll_pause_seconds: float = 1.5     # Her scroll sonrasi bekleme (siteye nazik davranmak icin)
    max_scroll_attempts: int = 60         # Sonsuz dongu koruma limiti
    page_load_timeout: int = 20
    output_dir: str = os.path.join(os.path.dirname(__file__), "..", "data")

    # BURAYI HEDEF SITEYE GORE GUNCELLEYIN (DevTools ile inceleyip doldurun)
    # Sag taraftaki degerler ORNEK/YER TUTUCU css secicileridir.
    selectors: dict = field(default_factory=lambda: {
        "cookie_accept_button": "#onetrust-accept-btn-handler",   # Cerez onay butonu (varsa)
        "review_card": "div.review-card",                        # Her bir yorum kartinin container'i
        "review_text": "p.review-text, div.comment-text",        # Yorum metni elementi (kart icinde)
        "load_more_button": "button.load-more, a.load-more",     # "Daha fazla goster" butonu (varsa)
        # Sonsuz scroll bazi sitelerde otomatik yeni icerik yukler; bu durumda
        # load_more_button gerekmez, sadece scroll yeterlidir.
    })


# ----------------------------------------------------------------------------
# YARDIMCI FONKSIYONLAR
# ----------------------------------------------------------------------------
def build_driver(config: ScraperConfig) -> webdriver.Chrome:
    """WebDriver Manager kullanarak otomatik Chrome sürücüsü kurar ve baslatir."""
    options = Options()
    if config.headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,1000")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Bot algilanmasini azaltmak icin gercekci bir User-Agent kullanilir
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
    options.add_argument("--log-level=3")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(config.page_load_timeout)
        return driver
    except WebDriverException as exc:
        logger.error("ChromeDriver baslatilamadi: %s", exc)
        raise


def clean_text(raw_text: str) -> str:
    """Yorum metnini gereksiz bosluk/satir aralarindan arindirir."""
    if not raw_text:
        return ""
    text = re.sub(r"\s+", " ", raw_text).strip()
    return text


def dismiss_cookie_banner(driver: webdriver.Chrome, config: ScraperConfig) -> None:
    """Sayfa acildiginda cikan cerez onay banner'ini kapatmayi dener (varsa)."""
    try:
        button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, config.selectors["cookie_accept_button"]))
        )
        button.click()
        logger.info("Cerez onay banner'i kapatildi.")
    except (TimeoutException, NoSuchElementException):
        # Banner yoksa sorun degil, devam edilir
        logger.debug("Cerez banner'i bulunamadi, devam ediliyor.")


def scroll_and_collect(driver: webdriver.Chrome, config: ScraperConfig) -> list[str]:
    """
    Infinite scroll mantigini cozerek sayfadaki tum yorumlari toplar.
    Her scroll sonrasi sayfa yuksekligi degismiyorsa (yeni icerik gelmiyorsa)
    dongu sonlandirilir. Ayrica bir 'load more' butonu varsa onu da tetikler.
    """
    collected_texts: set[str] = set()
    last_height = driver.execute_script("return document.body.scrollHeight")

    for attempt in range(1, config.max_scroll_attempts + 1):
        # 1) Sayfayi en alta kaydir
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(config.scroll_pause_seconds)

        # 2) Varsa "Daha Fazla Goster" butonuna tikla
        try:
            load_more = driver.find_element(By.CSS_SELECTOR, config.selectors["load_more_button"])
            if load_more.is_displayed() and load_more.is_enabled():
                driver.execute_script("arguments[0].click();", load_more)
                time.sleep(config.scroll_pause_seconds)
        except (NoSuchElementException, StaleElementReferenceException):
            pass  # Buton yoksa saf infinite-scroll mantigi calisir

        # 3) Su ana kadar yuklenen yorumlari topla
        try:
            cards = driver.find_elements(By.CSS_SELECTOR, config.selectors["review_card"])
            for card in cards:
                try:
                    text_el = card.find_element(By.CSS_SELECTOR, config.selectors["review_text"])
                    cleaned = clean_text(text_el.text)
                    if cleaned:
                        collected_texts.add(cleaned)
                except (NoSuchElementException, StaleElementReferenceException):
                    continue
        except WebDriverException as exc:
            logger.warning("Yorum kartlari okunurken hata: %s", exc)

        # 4) Yeni icerik gelip gelmedigini kontrol et
        new_height = driver.execute_script("return document.body.scrollHeight")
        logger.info(
            "Scroll #%d | Toplam benzersiz yorum: %d | Sayfa yuksekligi: %d",
            attempt, len(collected_texts), new_height,
        )
        if new_height == last_height:
            logger.info("Sayfa sonuna ulasildi, yeni icerik yok. Toplama tamamlandi.")
            break
        last_height = new_height

    return list(collected_texts)


def save_to_files(reviews: list[str], config: ScraperConfig) -> str:
    """
    Toplanan yorumlari DataFrame'e aktarir ve istenen kolon semasi ile
    CSV + Excel olarak diske yazar.

    Not: "Duygu", "Kategori", "Örnek Yanıt" kolonlari kasitli olarak bos
    birakilir. Bu kolonlar, RAG sisteminin referans alacagi "gecmis
    ornekleri" temsil eder ve misafir iliskileri ekibi tarafindan (veya
    ayri bir on-etiketleme adiminda) doldurulmalidir. Bu sekilde RAG
    motoru sadece GUVENILIR, insan onayli cevaplari referans alir.
    """
    os.makedirs(config.output_dir, exist_ok=True)

    df = pd.DataFrame({
        "Yorum": reviews,
        "Duygu": ["" for _ in reviews],          # Ornek: Pozitif / Notr / Negatif
        "Kategori": ["" for _ in reviews],        # Ornek: Temizlik / Yemek / Personel / Oda
        "Örnek Yanıt": ["" for _ in reviews],     # Insan onayli, kurumsal uslupla yazilmis cevap
    })

    csv_path = os.path.join(config.output_dir, "yorumlar_ham.csv")
    xlsx_path = os.path.join(config.output_dir, "yorumlar_ham.xlsx")

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")  # utf-8-sig: Excel'de Turkce karakter sorunu olmasin
    df.to_excel(xlsx_path, index=False, engine="openpyxl")

    logger.info("CSV kaydedildi: %s", csv_path)
    logger.info("Excel kaydedildi: %s", xlsx_path)
    return csv_path


# ----------------------------------------------------------------------------
# ANA AKIS
# ----------------------------------------------------------------------------
def run_scraper(config: ScraperConfig) -> None:
    driver = None
    try:
        logger.info("ChromeDriver baslatiliyor...")
        driver = build_driver(config)

        logger.info("Hedef sayfa aciliyor: %s", config.target_url)
        driver.get(config.target_url)

        dismiss_cookie_banner(driver, config)

        # Sayfanin temel iceriginin yuklenmesini bekle
        try:
            WebDriverWait(driver, config.page_load_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, config.selectors["review_card"]))
            )
        except TimeoutException:
            logger.error(
                "Yorum kartlari bulunamadi. SELECTORS['review_card'] degerini "
                "DevTools ile kontrol edip guncelleyin."
            )
            return

        reviews = scroll_and_collect(driver, config)

        if not reviews:
            logger.warning("Hic yorum toplanamadi. Secicileri (selectors) kontrol edin.")
            return

        logger.info("Toplam %d benzersiz yorum toplandi.", len(reviews))
        save_to_files(reviews, config)

    except WebDriverException as exc:
        logger.error("Tarayici/WebDriver hatasi: %s", exc)
    except Exception as exc:  # noqa: BLE001 - beklenmedik hatalari da loglayip programi cokertmemek icin
        logger.exception("Beklenmedik bir hata olustu: %s", exc)
    finally:
        if driver is not None:
            driver.quit()
            logger.info("Tarayici kapatildi.")


if __name__ == "__main__":
    cfg = ScraperConfig()
    run_scraper(cfg)
