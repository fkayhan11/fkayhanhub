import os
import json
import subprocess
import glob

image_dir = "/Users/furkanmacbook/Desktop/Excel/yorumssleri"
ocr_bin = "/Users/furkanmacbook/Desktop/Excel/ocr"
images = glob.glob(os.path.join(image_dir, "*.png"))

all_pairs = []
for idx, img in enumerate(images):
    print(f"[{idx+1}/{len(images)}] Okunuyor: {os.path.basename(img)}")
    result = subprocess.run([ocr_bin, img], capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        data.sort(key=lambda x: x['y'], reverse=True)
        text = " ".join([item['text'] for item in data])
        all_pairs.append(text)
    except Exception as e:
        print("Hata:", e)

with open("data/few_shot.txt", "w", encoding="utf-8") as f:
    for i, t in enumerate(all_pairs):
        f.write(f"--- ÖRNEK {i+1} ---\n{t}\n\n")

print("OCR Tamamlandı, data/few_shot.txt oluşturuldu.")
