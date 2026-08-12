import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Ortam değişkenlerinden yapılandırmaları al
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-pro") # Fallback değer

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

CSV_PATH = 'data/yorumlar_referans.csv'

def load_data():
    try:
        df = pd.read_csv(CSV_PATH)
        return df.dropna()
    except FileNotFoundError:
        # Gerçek veri yoksa iskelet çalışsın diye 10 adet dummy veri oluşturulur
        return pd.DataFrame({
            "user_review": ["Otel çok temizdi, yemekler harikaydı.", "Personel ilgisizdi ve oda temizlenmemişti."],
            "hotel_response": ["Güzel yorumlarınız için teşekkür ederiz, tekrar bekleriz.", "Yaşadığınız olumsuz deneyim için özür dileriz, telafi etmek isteriz."]
        })

def get_similar_reviews(new_review, df, top_k=3):
    if df.empty:
        return []
    
    vectorizer = TfidfVectorizer()
    all_reviews = df['user_review'].tolist()
    all_reviews.append(new_review)
    
    tfidf_matrix = vectorizer.fit_transform(all_reviews)
    cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    
    top_indices = cosine_sim.argsort()[-top_k:][::-1]
    
    similar_contexts = []
    for idx in top_indices:
        similar_contexts.append({
            "review": df.iloc[idx]['user_review'],
            "response": df.iloc[idx]['hotel_response'],
            "score": cosine_sim[idx]
        })
    return similar_contexts

def generate_ai_response(new_review):
    df = load_data()
    similar_contexts = get_similar_reviews(new_review, df)
    
    context_text = "\n\n".join([f"Geçmiş Yorum: {c['review']}\nVerilen Yanıt: {c['response']}" for c in similar_contexts])
    
    prompt = f"""
    Sen beş yıldızlı kurumsal bir otelin misafir ilişkileri yöneticisisin. 
    Aşağıdaki yeni misafir yorumuna, otelin geçmişteki yanıt dilini ve üslubunu (referanslardan analiz ederek) referans alarak profesyonel, nazik ve çözüm odaklı bir yanıt yaz.
    
    --- REFERANS GEÇMİŞ YANITLAR ---
    {context_text}
    
    --- YENİ MİSAFİR YORUMU ---
    {new_review}
    
    Lütfen sadece doğrudan misafire verilecek yanıtı üret.
    """
    
    response = model.generate_content(prompt)
    return response.text