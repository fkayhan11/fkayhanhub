/* ============================================================================
   script.js
   Guest Relations Terminal — Vanilla JS SPA mantığı.

   NOT: Backend, frontend'i /static altında ve "/" üzerinden servis eder
   (bkz. backend/main.py). Bu yüzden API_BASE_URL göreli ("") bırakılmıştır.
   Eğer index.html'i backend'den BAĞIMSIZ, doğrudan dosya olarak (file://)
   açacaksanız, API_BASE_URL değerini "http://127.0.0.1:8000" yapın.
============================================================================ */

const API_BASE_URL = ""; // Aynı origin üzerinden servis ediliyorsa boş kalabilir
const GENERATE_ENDPOINT = `${API_BASE_URL}/api/generate-response`;
const HEALTH_ENDPOINT = `${API_BASE_URL}/api/health`;

// ---------------------------------------------------------------------------
// DOM REFERANSLARI
// ---------------------------------------------------------------------------
const reviewInput = document.getElementById("reviewInput");
const charCount = document.getElementById("charCount");
const generateBtn = document.getElementById("generateBtn");
const btnSpinner = document.getElementById("btnSpinner");
const errorBox = document.getElementById("errorBox");
const referencesList = document.getElementById("referencesList");
const aiResponseBox = document.getElementById("aiResponseBox");
const copyBtn = document.getElementById("copyBtn");
const copyBtnLabel = document.getElementById("copyBtnLabel");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const modelBadge = document.getElementById("modelBadge");
const clockEl = document.getElementById("clock");

let lastGeneratedResponse = "";

// ---------------------------------------------------------------------------
// SAAT (Terminal hissi için sağ alt köşede canlı saat)
// ---------------------------------------------------------------------------
function tickClock() {
  const now = new Date();
  clockEl.textContent = now.toLocaleTimeString("tr-TR", { hour12: false });
}
tickClock();
setInterval(tickClock, 1000);

// ---------------------------------------------------------------------------
// KARAKTER SAYACI
// ---------------------------------------------------------------------------
reviewInput.addEventListener("input", () => {
  charCount.textContent = reviewInput.value.length;
});

// ---------------------------------------------------------------------------
// SISTEM DURUMU (Backend health-check)
// ---------------------------------------------------------------------------
async function checkHealth() {
  try {
    const res = await fetch(HEALTH_ENDPOINT);
    if (!res.ok) throw new Error("health check failed");
    const data = await res.json();

    modelBadge.textContent = `MODEL: ${data.model || "—"}`;

    if (data.status === "ready") {
      statusDot.className = "status-dot is-live";
      statusText.textContent = `HAZIR · ${data.dataset_size} KAYIT`;
    } else {
      statusDot.className = "status-dot is-error";
      statusText.textContent = "VERİ SETİ YOK";
    }
  } catch (err) {
    statusDot.className = "status-dot is-error";
    statusText.textContent = "BAĞLANTI YOK";
    modelBadge.textContent = "MODEL: —";
  }
}
checkHealth();
setInterval(checkHealth, 30000); // her 30 saniyede bir durumu tazele

// ---------------------------------------------------------------------------
// YARDIMCI: HTML KAÇIŞ (XSS koruması — API'den gelen metni doğrudan
// innerHTML'e basmadan önce kaçış yapıyoruz)
// ---------------------------------------------------------------------------
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function sentimentTagClass(duygu) {
  const normalized = (duygu || "").toLowerCase();
  if (normalized.includes("pozitif")) return "tag--positive";
  if (normalized.includes("negatif")) return "tag--negative";
  return "tag--notr";
}

// ---------------------------------------------------------------------------
// REFERANS KARTLARINI RENDER ET
// ---------------------------------------------------------------------------
function renderReferences(references) {
  if (!references || references.length === 0) {
    referencesList.innerHTML = `
      <div class="empty-state empty-state--small">
        <span class="empty-state__icon">▤</span>
        <p>Bu yoruma benzer referans kayıt bulunamadı.</p>
      </div>`;
    return;
  }

  referencesList.innerHTML = references
    .map((ref) => {
      const scorePercent = Math.round((ref.benzerlik_skoru || 0) * 100);
      return `
        <div class="reference-card">
          <div class="reference-card__top">
            <div class="reference-card__tags">
              <span class="tag ${sentimentTagClass(ref.duygu)}">${escapeHtml(ref.duygu || "—")}</span>
              <span class="tag">${escapeHtml(ref.kategori || "—")}</span>
            </div>
            <div class="similarity-meter" title="Cosine similarity skoru">
              <span>${scorePercent}%</span>
              <div class="similarity-meter__bar">
                <div class="similarity-meter__fill" style="width:${scorePercent}%"></div>
              </div>
            </div>
          </div>
          <p class="reference-card__review">"${escapeHtml(ref.yorum)}"</p>
          <p class="reference-card__answer">
            <span class="reference-card__answer-label">Kurumsal Yanıt</span>
            ${escapeHtml(ref.ornek_yanit)}
          </p>
        </div>`;
    })
    .join("");
}

// ---------------------------------------------------------------------------
// HATA GÖSTERİMİ
// ---------------------------------------------------------------------------
function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}
function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}

// ---------------------------------------------------------------------------
// YÜKLENİYOR DURUMU
// ---------------------------------------------------------------------------
function setLoading(isLoading) {
  generateBtn.disabled = isLoading;
  btnSpinner.hidden = !isLoading;
  generateBtn.querySelector(".btn__label").textContent = isLoading
    ? "Üretiliyor..."
    : "Yanıt Üret";
}

// ---------------------------------------------------------------------------
// ANA İŞLEM: "Yanıt Üret" BUTONU
// ---------------------------------------------------------------------------
const nameModal = document.getElementById("nameModal");
const guestNameInput = document.getElementById("guestNameInput");
const modalCancelBtn = document.getElementById("modalCancelBtn");
const modalConfirmBtn = document.getElementById("modalConfirmBtn");

generateBtn.addEventListener("click", () => {
  const yorum = reviewInput.value.trim();
  clearError();
  if (yorum.length < 3) {
    showError("Lütfen en az 3 karakter uzunluğunda bir yorum girin.");
    return;
  }
  nameModal.hidden = false;
  guestNameInput.value = "";
  guestNameInput.focus();
});

modalCancelBtn.addEventListener("click", () => {
  nameModal.hidden = true;
});

modalConfirmBtn.addEventListener("click", () => {
  nameModal.hidden = true;
  const guestName = guestNameInput.value.trim();
  handleGenerate(guestName);
});

async function handleGenerate(guestName = "") {
  const yorum = reviewInput.value.trim();
  setLoading(true);
  copyBtn.hidden = true;

  try {
    const response = await fetch(GENERATE_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ yorum, guest_name: guestName }),
    });

    // HTTP durum koduna göre anlamlı hata mesajları (backend'deki
    // HTTPException detay alanlarıyla birebir eşleşir)
    if (!response.ok) {
      let detail = `Sunucu hatası (HTTP ${response.status}).`;
      try {
        const errJson = await response.json();
        if (errJson.detail) detail = errJson.detail;
      } catch (_) {
        /* JSON parse edilemiyorsa varsayılan mesaj kullanılır */
      }

      if (response.status === 429) {
        throw new Error(`⏱ İstek limiti aşıldı: ${detail}`);
      }
      if (response.status === 503) {
        throw new Error(`⚠ Servis hazır değil: ${detail}`);
      }
      if (response.status === 502) {
        throw new Error(`🔌 Yapay zeka servisine ulaşılamadı: ${detail}`);
      }
      throw new Error(detail);
    }

    const data = await response.json();

    renderReferences(data.references);

    lastGeneratedResponse = data.ai_response || "";
    aiResponseBox.innerHTML = `<p style="margin:0;">${escapeHtml(lastGeneratedResponse)}</p>`;

    copyBtn.hidden = false;
    copyBtn.classList.remove("is-copied");
    copyBtnLabel.textContent = "Panoya Kopyala";
  } catch (err) {
    console.error(err);
    showError(err.message || "Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.");
  } finally {
    setLoading(false);
  }
}

// Ctrl/Cmd + Enter ile hızlı gönderim (terminal kullanıcıları için pratik kısayol)
reviewInput.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    generateBtn.click();
  }
});

// ---------------------------------------------------------------------------
// PANOYA KOPYALAMA
// ---------------------------------------------------------------------------
copyBtn.addEventListener("click", async () => {
  if (!lastGeneratedResponse) return;
  try {
    await navigator.clipboard.writeText(lastGeneratedResponse);
    copyBtn.classList.add("is-copied");
    copyBtnLabel.textContent = "✓ Kopyalandı";
    setTimeout(() => {
      copyBtn.classList.remove("is-copied");
      copyBtnLabel.textContent = "Panoya Kopyala";
    }, 2000);
  } catch (err) {
    // Clipboard API bazi tarayicilarda/http olmayan ortamlarda basarisiz olabilir
    showError("Panoya kopyalama başarısız oldu. Metni manuel olarak seçip kopyalayabilirsiniz.");
  }
});
