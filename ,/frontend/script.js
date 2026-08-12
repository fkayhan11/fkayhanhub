document.getElementById('generateBtn').addEventListener('click', async () => {
    const reviewText = document.getElementById('reviewInput').value;
    const aiResponseDiv = document.getElementById('aiResponse');
    const loadingDiv = document.getElementById('loading');

    if (!reviewText.trim()) {
        alert('Lütfen bir misafir yorumu girin.');
        return;
    }

    aiResponseDiv.classList.add('hidden');
    loadingDiv.classList.remove('hidden');

    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ review_text: reviewText })
        });

        const data = await response.json();
        
        loadingDiv.classList.add('hidden');
        aiResponseDiv.classList.remove('hidden');
        aiResponseDiv.textContent = data.response;
        
    } catch (error) {
        loadingDiv.classList.add('hidden');
        aiResponseDiv.classList.remove('hidden');
        aiResponseDiv.textContent = 'Bir hata oluştu. Lütfen backend bağlantısını kontrol edin.';
        console.error('Error:', error);
    }
});

document.getElementById('copyBtn').addEventListener('click', () => {
    const aiResponseDiv = document.getElementById('aiResponse');
    navigator.clipboard.writeText(aiResponseDiv.textContent).then(() => {
        alert('Yanıt panoya kopyalandı!');
    });
});