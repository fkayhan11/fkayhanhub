import React, { useState, useEffect, useRef } from 'react';
import QRCode from 'qrcode';
import {
  QrCode,
  Link2,
  Image as ImageIcon,
  Palette,
  Check,
  Globe2,
  ShieldCheck,
  Download,
  Copy,
  UploadCloud,
  Loader2,
  X
} from 'lucide-react';

const COLOR_THEMES = [
  { id: 'midnight', name: 'Midnight', color: '#1e293b' },
  { id: 'ocean', name: 'Ocean', color: '#2563eb' },
  { id: 'emerald', name: 'Emerald', color: '#059669' },
  { id: 'orange', name: 'Orange', color: '#ea580c' },
  { id: 'crimson', name: 'Crimson', color: '#dc2626' },
  { id: 'amber', name: 'Amber', color: '#d97706' },
  { id: 'purple', name: 'Purple', color: '#7c3aed' },
  { id: 'teal', name: 'Teal', color: '#0d9488' },
  { id: 'ruby', name: 'Ruby', color: '#be123c' },
  { id: 'green', name: 'Green', color: '#16a34a' },
  { id: 'slate', name: 'Slate', color: '#475569' },
  { id: 'indigo', name: 'Indigo', color: '#4f46e5' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<'link' | 'image'>('link');
  const [textInput, setTextInput] = useState('');
  const [selectedTheme, setSelectedTheme] = useState(COLOR_THEMES[1]);
  
  // Output
  const [qrDataUrl, setQrDataUrl] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);

  // Image Upload State
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedImageUrl, setUploadedImageUrl] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sekme değiştiğinde önizlemeyi temizle
  useEffect(() => {
    setQrDataUrl('');
  }, [activeTab]);

  const handleGenerateClick = () => {
    const input = activeTab === 'image' ? uploadedImageUrl : textInput;
    
    if (!input.trim()) {
      alert(activeTab === 'link' ? "Lütfen bir link girin." : "Lütfen önce bir resim yükleyin.");
      return;
    }

    setIsGenerating(true);
    setQrDataUrl(''); // Yeni üretim başlarken eski resmi gizle
    
    // UX için animasyonlu bekleme süresi
    setTimeout(() => {
      let finalUrl = input.trim();
      if (activeTab === 'link' && !/^https?:\/\//i.test(finalUrl) && finalUrl.includes('.')) {
        finalUrl = 'https://' + finalUrl;
      }

      QRCode.toDataURL(finalUrl, {
        width: 400,
        margin: 2,
        color: {
          dark: selectedTheme.color,
          light: '#ffffff',
        },
        errorCorrectionLevel: 'H',
      })
        .then((url) => setQrDataUrl(url))
        .catch((err) => console.error('QR generation error:', err))
        .finally(() => setIsGenerating(false));
    }, 600); // 600ms loading efekti
  };

  const handleDownload = () => {
    if (!qrDataUrl) return;
    const link = document.createElement('a');
    link.download = `QR_Kod_${selectedTheme.name}.png`;
    link.href = qrDataUrl;
    link.click();
  };

  const handleCopy = async () => {
    if (!qrDataUrl) return;
    try {
      const res = await fetch(qrDataUrl);
      const blob = await res.blob();
      await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': blob }),
      ]);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Kopyalama hatası:', err);
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const apiKey = import.meta.env.VITE_IMGBB_API_KEY;
    if (!apiKey) {
      alert("HATA: ImgBB API Anahtarı eksik! Lütfen .env dosyanıza VITE_IMGBB_API_KEY değerini ekleyin ve sunucuyu yeniden başlatın.");
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('image', file);

      const res = await fetch(`https://api.imgbb.com/1/upload?key=${apiKey}`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (data.success) {
        setUploadedImageUrl(data.data.url);
        setQrDataUrl(''); // Yeni resim yüklendiğinde eski QR kodu temizle
      } else {
        throw new Error(data.error?.message || 'Yükleme başarısız');
      }
    } catch (err: any) {
      alert("Resim yüklenirken hata oluştu: " + err.message);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const clearUploadedImage = () => {
    setUploadedImageUrl('');
    setQrDataUrl('');
  };

  return (
    <div className="min-h-screen bg-[#f4f9f8] text-slate-800 font-sans selection:bg-indigo-500 selection:text-white pb-16 flex flex-col">
      {/* Header Section */}
      <div className="w-full flex flex-col items-center pt-16 pb-12 px-4 text-center">
        <div className="w-16 h-16 bg-slate-900 rounded-2xl flex items-center justify-center mb-6 shadow-xl shadow-slate-900/10">
          <QrCode className="w-8 h-8 text-white stroke-[1.5]" />
        </div>
        <h1 className="text-4xl font-bold text-slate-900 mb-4 tracking-tight">
          QR Kod Stüdyosu
        </h1>
        <p className="text-slate-500 text-lg max-w-xl">
          Linklerinizi ve resimlerinizi anında şık QR kodlara dönüştürün. Süresiz, sorunsuz ve tamamen ücretsiz.
        </p>
      </div>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 w-full flex-1">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          
          {/* Left Panel: Inputs */}
          <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-slate-100 flex flex-col space-y-8">
            
            {/* Tabs */}
            <div className="bg-slate-50 p-1.5 rounded-2xl flex gap-1 border border-slate-100">
              <button
                onClick={() => setActiveTab('link')}
                className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-medium text-sm transition-all duration-200 ${
                  activeTab === 'link'
                    ? 'bg-white text-slate-800 shadow-sm border border-slate-200/50'
                    : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100/50'
                }`}
              >
                <Link2 className="w-4 h-4" />
                Link
              </button>
              <button
                onClick={() => setActiveTab('image')}
                className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-medium text-sm transition-all duration-200 ${
                  activeTab === 'image'
                    ? 'bg-white text-slate-800 shadow-sm border border-slate-200/50'
                    : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100/50'
                }`}
              >
                <ImageIcon className="w-4 h-4" />
                Resim
              </button>
            </div>

            {/* Input Section */}
            {activeTab === 'link' ? (
              <div className="space-y-3 animate-in fade-in duration-300">
                <label className="text-sm font-semibold text-slate-700">Link adresi</label>
                <input
                  type="text"
                  value={textInput}
                  onChange={(e) => {
                    setTextInput(e.target.value);
                    setQrDataUrl(''); // Metin değiştiğinde QR'ı temizle
                  }}
                  placeholder="ornek.com veya https://ornek.com"
                  className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-5 py-4 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-[15px]"
                />
                <p className="text-xs text-slate-500 leading-relaxed pt-1">
                  İstediğiniz herhangi bir linki yapıştırın — web sitesi, sosyal medya, YouTube videosu, PDF dokümanı...
                </p>
              </div>
            ) : (
              <div className="space-y-3 animate-in fade-in duration-300">
                <label className="text-sm font-semibold text-slate-700">Resim Yükle</label>
                
                {!uploadedImageUrl ? (
                  <div 
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full border-2 border-dashed border-slate-300 rounded-2xl p-8 flex flex-col items-center justify-center gap-3 bg-slate-50 hover:bg-slate-100 transition-colors cursor-pointer"
                  >
                    {isUploading ? (
                      <>
                        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                        <p className="text-sm font-medium text-slate-600">Yükleniyor...</p>
                      </>
                    ) : (
                      <>
                        <div className="p-3 bg-white rounded-full shadow-sm">
                          <UploadCloud className="w-6 h-6 text-blue-500" />
                        </div>
                        <div className="text-center">
                          <p className="text-sm font-medium text-slate-700">Tıklayın veya resmi sürükleyin</p>
                          <p className="text-xs text-slate-500 mt-1">PNG, JPG, GIF (Maks. 32MB)</p>
                        </div>
                      </>
                    )}
                    <input 
                      type="file" 
                      ref={fileInputRef}
                      onChange={handleImageUpload}
                      accept="image/*"
                      className="hidden"
                    />
                  </div>
                ) : (
                  <div className="relative border border-slate-200 rounded-2xl p-2 bg-slate-50 flex justify-center items-center min-h-[12rem]">
                    <img 
                      src={uploadedImageUrl} 
                      alt="Yüklenen resim" 
                      className="max-w-full h-auto max-h-48 object-contain rounded-xl shadow-sm"
                    />
                    <button 
                      onClick={clearUploadedImage}
                      className="absolute top-4 right-4 p-1.5 bg-black/50 hover:bg-black/70 text-white rounded-full backdrop-blur-sm transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                )}
                <p className="text-xs text-slate-500 leading-relaxed pt-1">
                  Resminiz ImgBB sunucularına kalıcı ve güvenli bir şekilde yüklenir.
                </p>
              </div>
            )}

            {/* Color Theme Section */}
            <div className="space-y-4 pt-2 border-t border-slate-100">
              <label className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                <Palette className="w-4 h-4 text-slate-400" />
                Renk teması
              </label>
              
              <div className="grid grid-cols-6 sm:grid-cols-6 gap-3">
                {COLOR_THEMES.map((theme) => {
                  const isSelected = selectedTheme.id === theme.id;
                  return (
                    <button
                      key={theme.id}
                      onClick={() => {
                        setSelectedTheme(theme);
                        setQrDataUrl(''); // Tema değiştiğinde eski QR'ı temizle
                      }}
                      className={`relative aspect-square rounded-xl transition-all duration-200 focus:outline-none ${
                        isSelected ? 'ring-2 ring-blue-500 ring-offset-2 scale-110 shadow-md z-10' : 'hover:scale-105 hover:shadow-sm'
                      }`}
                      style={{ backgroundColor: theme.color }}
                      title={theme.name}
                    >
                      {isSelected && (
                        <div className="absolute inset-0 flex items-center justify-center">
                          <Check className="w-5 h-5 text-white drop-shadow-md" />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-slate-500 font-medium">
                Seçili: <span className="text-slate-700">{selectedTheme.name}</span>
              </p>
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerateClick}
              disabled={isGenerating || (activeTab === 'link' ? !textInput.trim() : !uploadedImageUrl)}
              className={`w-full py-4 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-[15px] flex items-center justify-center gap-2 transition-all shadow-md shadow-blue-600/20 disabled:opacity-50 disabled:cursor-not-allowed ${
                isGenerating ? 'scale-[0.98]' : ''
              }`}
            >
              {isGenerating ? <Loader2 className="w-5 h-5 animate-spin" /> : <QrCode className="w-5 h-5" />}
              {isGenerating ? 'Oluşturuluyor...' : 'QR Kod Oluştur'}
            </button>
          </div>

          {/* Right Panel: Preview */}
          <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-slate-100 h-full flex flex-col">
            <h3 className="font-semibold text-slate-800 flex items-center gap-2 mb-8">
              <QrCode className="w-5 h-5 text-slate-400" />
              QR Kod Önizleme
            </h3>

            <div className="flex-1 flex flex-col items-center justify-center min-h-[300px]">
              {isGenerating ? (
                <div className="flex flex-col items-center justify-center space-y-4 animate-in fade-in">
                  <Loader2 className="w-12 h-12 text-blue-500 animate-spin" />
                  <p className="text-sm font-medium text-slate-500">QR Kodunuz Hazırlanıyor...</p>
                </div>
              ) : qrDataUrl ? (
                <div className="flex flex-col items-center animate-in fade-in zoom-in duration-300">
                  <div className="p-4 bg-white rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 mb-8">
                    <img
                      src={qrDataUrl}
                      alt="Oluşturulan QR Kod"
                      className="w-56 h-56 sm:w-64 sm:h-64 object-contain rounded-xl"
                    />
                  </div>
                  
                  <div className="flex items-center gap-3 w-full max-w-[280px]">
                    <button
                      onClick={handleDownload}
                      className="flex-1 py-3 px-4 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm flex items-center justify-center gap-2 transition-all shadow-sm shadow-blue-600/20"
                    >
                      <Download className="w-4 h-4" />
                      İndir
                    </button>
                    <button
                      onClick={handleCopy}
                      className="flex-1 py-3 px-4 rounded-2xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium text-sm flex items-center justify-center gap-2 transition-all"
                    >
                      {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                      Kopyala
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center text-center max-w-xs animate-in fade-in">
                  <div className="w-24 h-24 border-2 border-dashed border-slate-200 rounded-3xl flex items-center justify-center mb-6">
                    <QrCode className="w-10 h-10 text-slate-300 stroke-[1.5]" />
                  </div>
                  <h4 className="font-semibold text-slate-700 mb-2">QR kodunuz burada görünecek</h4>
                  <p className="text-sm text-slate-400">
                    Önce linkinizi veya resminizi girin, rengi seçin ve <strong>"QR Kod Oluştur"</strong> butonuna basın.
                  </p>
                </div>
              )}
            </div>
          </div>

        </div>

        {/* Info Cards Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
          <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-start gap-4">
            <div className="p-2.5 bg-slate-50 rounded-xl text-slate-500">
              <Globe2 className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-semibold text-sm text-slate-800 mb-1">Dünya çapında uyumlu</h4>
              <p className="text-xs text-slate-500 leading-relaxed">Kısa linkler ve standart format — tüm cihazlarda taranır</p>
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-start gap-4">
            <div className="p-2.5 bg-slate-50 rounded-xl text-slate-500">
              <Palette className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-semibold text-sm text-slate-800 mb-1">12 renk teması</h4>
              <p className="text-xs text-slate-500 leading-relaxed">Her tarza uygun şık renk seçenekleri</p>
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-start gap-4">
            <div className="p-2.5 bg-slate-50 rounded-xl text-slate-500">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-semibold text-sm text-slate-800 mb-1">Süresiz & yüksek koruma</h4>
              <p className="text-xs text-slate-500 leading-relaxed">Yüksek hata düzeltme ile hasara dayanıklı</p>
            </div>
          </div>
        </div>

        <div className="text-center mt-12 mb-4">
          <p className="text-xs text-slate-400">
            QR Kod Stüdyosu · Tüm QR kodları yüksek hata düzeltme ile oluşturulur
          </p>
        </div>
      </main>
    </div>
  );
}
