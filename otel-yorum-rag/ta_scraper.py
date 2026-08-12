import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def main():
    async with async_playwright() as p:
        # TripAdvisor'a yakalanmamak için User-Agent ve diğer parametreleri maskeliyoruz
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()
        
        print("TripAdvisor arama sayfasına gidiliyor...")
        # Asteria Family Resort Belek araması
        await page.goto('https://www.tripadvisor.com.tr/Search?q=Asteria%20Family%20Resort%20Belek', timeout=60000)
        
        print("Arama sonuçlarının yüklenmesi bekleniyor...")
        await page.wait_for_timeout(8000) # Sonuçların gelmesi için
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Sonuçlardan linkleri bul
        links = soup.find_all('a', href=True)
        hotel_url = None
        for link in links:
            href = link['href']
            if 'Hotel_Review' in href and 'Asteria' in href:
                hotel_url = 'https://www.tripadvisor.com.tr' + href
                break
                
        if not hotel_url:
            print("HATA: Arama sonuçlarında otel linki bulunamadı. Kaynak koduna bakılıyor...")
            with open("ta_search.html", "w", encoding="utf-8") as f:
                f.write(content)
        else:
            print(f"BULDUM! Otel Linki: {hotel_url}")
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
