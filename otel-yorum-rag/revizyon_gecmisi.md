# Otel Yorum RAG Sistemi - Revizyon ve Kural Geliştirme Geçmişi

Bu dosya, program ilk oluşturulduktan sonra yapay zekanın (LLM) misafirlere verdiği yanıtları mükemmelleştirmek ve standart "robotik" cevaplardan (örn. klasik Chat Gemini tarzı) çok daha üstün, elit bir kurumsal otelcilik diline ulaşmak için yapılan tüm ince ayarları (prompt engineering) içermektedir.

## Ana Felsefe (Kural 0)
Sistemin en temel iletişim stratejisi şudur: **"Hem misafiri asla üzmemek ve kırmamak, hem de oteli asla ve asla kötülememek."** Yapay zeka tamamen soğukkanlı, profesyonel, objektif ve elit bir kriz yönetimi dili benimsemelidir.

## Yapılan İyileştirmeler ve Eklenen Kurallar

### 1. Yapay Zeka Tekrarının Önlenmesi
- **Sorun:** Yapay zeka "memnuniyet", "teşekkür" gibi kelimeleri aynı metin içinde sürekli tekrarlıyordu.
- **Çözüm:** "Teşekkür, memnuniyet veya özür gibi kalıp ifadeleri aynı metin içinde tekrar tekrar KULLANMA. Cümleleri uzatmak için kelimeleri döngüye sokma" kuralı eklendi.

### 2. Aşırı Şiirsel ve Duygusal Dilin Kaldırılması
- **Sorun:** "Arınma hissi", "büyülü bir serüven" gibi otelcilik sektörüne uymayan aşırı edebi ve tuhaf ifadeler kullanılıyordu.
- **Çözüm:** Bu tarz şiirsel ve abartılı ifadeler kesinlikle yasaklandı. Sadece ciddi, standart ve kurumsal otelcilik diline dönüldü.

### 3. Savunma Mekanizması ve Mütevazılık
- **Sorun:** Gelen her şikayete "hemen düzelteceğiz" deniyor, otel gereksiz yere kendini eziyordu. Sonrasında savunma eklendiğinde ise "yüksek standartlar" gibi fazla kibirli ifadeler veya "personelimiz şöyle eğitiliyor" gibi gereksiz operasyonel detaylar ortaya çıktı.
- **Çözüm:** Şikayetlerin kayıtsız şartsız kabul edilmesi engellendi. Otelin "kurumsal kalite standartlarına uygun" hizmet verdiği mütevazı bir dille savunuldu. Mutfak, personel eğitimi gibi iç işleyiş detaylarına girilmesi kesin olarak yasaklandı.

### 4. Ayrıştırıcı Demografik İfadelerin Kaldırılması
- **Sorun:** Misafirlerin kullandığı "Yetişkin", "Türk", "Rus" gibi etnik veya yaşa dayalı kelimeler yanıtlarda birebir tekrarlanıyordu.
- **Çözüm:** Bu tür kelimelerin birebir kullanımı yasaklandı. Yerine "tüm misafir profilimiz", "farklı kültür ve yaş grupları" gibi kapsayıcı ve diplomatik (evrensel) kavramların kullanılması zorunlu kılındı.

### 5. Dinamik ve Eşsiz Giriş Cümleleri (Kalıpların Yasaklanması)
- **Sorun:** Her yanıt "Konaklamanızın ardından değerli görüşlerinizi paylaştığınız için teşekkür ederiz" gibi aynı fabrikasyon şablonla başlıyordu. Yorumları dışarıdan okuyan birisi bu tekrarı gördüğünde robotik olduğunu anlıyordu.
- **Çözüm:** Yanıtlara "Tesisimizde konakladığınız için..." veya "...için teşekkür ederiz" gibi klasik girişlerle başlanması **KESİN OLARAK YASAKLANDI**. Her yoruma, sadece o misafirin deneyimine özgü, sıradışı, yaratıcı ve yepyeni giriş cümleleriyle başlanması emredildi.

### 6. Zayıf İfadelerin ("Üzüntü duyduk", "Özür dileriz") Tamamen Yasaklanması
- **Sorun:** Otel şikayetlere yanıt verirken "üzüntü duyduk", "mağdur oldunuz", "özür dileriz" gibi kelimeler kullanarak suçu üstleniyor, duygusal ve zayıf ("ezik") bir imaj çiziyordu. Klasik LLM'lerin en büyük zayıflığı olan bu "yaranma" çabası kurumsal imaja zarar veriyordu.
- **Çözüm:** "Üzüldük", "özür dileriz", "mağduriyet" gibi kelimeler KESİNLİKLE yasaklandı. Otel hiçbir şekilde duygu belirtmeyecek (üzülmeyecek). Bunun yerine "Geri bildiriminiz dikkate alınmıştır", "İlgili departmanlarla paylaşılmıştır" şeklinde tamamen objektif, nötr, dik duran elit bir iletişim stratejisi benimsendi.

### 7. Akıcı ve Bütüncül Paragraflar (Robotik Listelemenin Engellenmesi)
- **Sorun:** Yapay zeka detay vermek isterken misafirin bahsettiği 5 farklı konuya mekanik bir şekilde tek tek cevap verip metni boğucu hale getiriyordu. (Bunu çözmek için cevaplar kısaltıldığında ise çok geçiştirici ve yetersiz oldu).
- **Çözüm:** "Yanıt detaylı ve açıklayıcı olmalıdır" kuralı geri getirildi ancak "konuları robotik bir liste gibi tek tek cevaplamak yerine, akıcı paragraflar halinde toparlayarak zarif bir bütünlük içinde sun" talimatı eklendi. Böylece doyurucu uzunluk korundu ama boğucu anlatım engellendi.

### 8. Kişiselleştirme ve Çeşitlilik (Şablonlaşmanın Kırılması)
- **Sorun:** Katı kurallara (özür dileme, detay verme vb.) uymaya çalışan yapay zeka, risk almamak için her yoruma neredeyse birbirinin kopyası olan aynı cümle yapıları ve aynı kalıplarla cevap vermeye başlamıştı. Yanıtlar kopyala-yapıştır gibi duruyordu.
- **Çözüm:** "Özgünlük ve Kişiselleştirme" kuralı eklenerek yapay zekanın her yanıtta zorunlu olarak farklı kelime grupları, çeşitli cümle yapıları ve benzersiz kurgular kullanması emredildi. Her cevabın misafire özel hissettirilmesi sağlandı.

### 9. Yapıcı Derinlik (Geçiştirici ve Kuru Üslubun Engellenmesi)
- **Sorun:** Yapay zeka "özür dileme" ve "detay verme" kurallarına uyarken metni aşırı kuru bir şekilde "Geri bildiriminiz iletildi, teşekkürler" modunda kesip atmaya, misafiri başından savmaya başladı.
- **Çözüm:** Yanıtlara "Kurumsal Derinlik" katması emredildi. Özür dilemeden ve oteli kötülemeden, misafir yorumlarının otelin vizyonuna olan katkısından bahsederek konuyu zarifçe ve dolgun bir şekilde toparlaması kuralı getirildi.

### 10. Son Revizyon: Kısıtlayıcı Kuralların "Vizyoner Karakter" (Persona) Formatına Dönüştürülmesi
- **Sorun:** Çok fazla negatif kural (onu yapma, bunu deme) yapay zekayı mekanikleştiriyor, "tatmin etmeyen" zoraki metinler çıkmasına yol açıyordu.
- **Çözüm:** Bütün liste maddeleri birleştirilerek yapay zekaya bir "Karakter (Persona)" yüklendi. Artık yapay zeka sıradan bir bot gibi kurallara uymaya çalışmıyor; kendisini otelin "En Saygın ve Elit Kurumsal İletişim Direktörü" olarak görüp sarsılmaz bir marka gururu, edebi zarafet ve kurumsal vizyonla eşsiz şaheserler yazıyor.

### 11. Altın Oran: Aşırı Edebi Dilin Doğal ve Yalın Kurumsallığa Çekilmesi
- **Sorun:** "Edebi ol, zarafet kat, vizyoner ol" gibi komutlar yapay zekayı fazla felsefi, karmaşık ve okuması zor, "kitap gibi" ağır bir dile yöneltti.
- **Çözüm:** Prompt optimize edilerek süslü, ağdalı ve edebi kelimeler tamamen çıkarıldı. Yapay zekanın "Doğal, Yalın, Anlaşılır ama son derece Elit ve Kurumsal" olması hedeflendi. Süslü kelimeler yasaklandı, böylece hem özür dilemeyen dik duruş korundu hem de konuşma akıcılığı çok daha doğal bir insan seviyesine getirildi.


