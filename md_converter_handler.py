import os
import json
import tempfile
import base64
import mammoth
from markdownify import markdownify
from google import genai
from dotenv import load_dotenv

def get_gemini_client():
    load_dotenv('otel-yorum-rag/.env')
    api_key = os.environ.get("GEMINI_API_KEY")
    model_name = os.environ.get("GEMINI_MODEL_NAME", "gemini-3.5-flash")
    if not api_key:
        return None, model_name
    return genai.Client(api_key=api_key), model_name

def handle_md_conversion(payload):
    docx_base64 = payload.get('docx_base64')
    raw_text = payload.get('text', '').strip()
    
    if not docx_base64 and not raw_text:
        return {"status": "error", "error": "Ne metin ne de Word dosyası sağlandı."}

    md_result = ""

    # 1. Eğer DOCX dosyası yüklendiyse (Mammoth + Markdownify)
    if docx_base64:
        try:
            # Decode base64 and write to temp file
            file_data = base64.b64decode(docx_base64.split(",")[1] if "," in docx_base64 else docx_base64)
            temp_fd, temp_path = tempfile.mkstemp(suffix=".docx")
            with os.fdopen(temp_fd, 'wb') as f:
                f.write(file_data)
            
            # Convert to HTML using mammoth
            with open(temp_path, "rb") as docx_file:
                result = mammoth.convert_to_html(docx_file)
                html = result.value
            
            os.remove(temp_path)
            
            # Convert HTML to Markdown
            md_result = markdownify(html, heading_style="ATX")
            
        except Exception as e:
            return {"status": "error", "error": f"Word dosyası işlenirken hata: {str(e)}"}

    # 2. Eğer sadece ham metin yapıştırıldıysa (Gemini ile Akıllı Markdown Formatlama)
    elif raw_text:
        client, model_name = get_gemini_client()
        if not client:
            return {"status": "error", "error": "Google API Key bulunamadı. Lütfen .env dosyasını kontrol edin."}
            
        prompt = (
            "Aşağıdaki ham metni profesyonelce biçimlendirilmiş bir Markdown (.md) metnine dönüştür.\n"
            "Gerektiğinde başlıklar (##), listeler (-), kalın/eğik yazılar kullanarak metni çok daha okunaklı ve şık hale getir. "
            "Sadece Markdown kodunu döndür, başına ve sonuna markdown bloğu işareti (```markdown) KOYMA.\n"
            "ÇOK ÖNEMLİ: Kesinlikle orijinal metinde olmayan hiçbir şeyi ekleme. Giriş cümlesi, kapanış cümlesi, özet veya 'Bu metin düzenlenmiştir' gibi ekstra yorumlar YAZMA. Sadece doğrudan orijinal metni biçimlendirerek ver.\n\n"
            f"--- METİN ---\n{raw_text}"
        )
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            md_result = response.text.strip()
            # Olası kod bloklarını temizle
            if md_result.startswith("```markdown"):
                md_result = md_result[11:]
            elif md_result.startswith("```md"):
                md_result = md_result[5:]
            if md_result.endswith("```"):
                md_result = md_result[:-3]
            md_result = md_result.strip()
        except Exception as e:
            return {"status": "error", "error": f"Yapay Zeka ile formatlanırken hata: {str(e)}"}

    return {
        "status": "success",
        "markdown": md_result
    }
