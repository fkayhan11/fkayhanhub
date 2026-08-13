import sys
import json
import pytesseract
from PIL import Image

def run_tesseract_ocr(image_path):
    img = Image.open(image_path)
    width, height = img.size
    
    # We use pytesseract to get detailed bounding box data
    data = pytesseract.image_to_data(img, lang='tur+eng', output_type=pytesseract.Output.DICT)
    
    results = []
    
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        # Ignore empty text or spaces
        if not text:
            continue
        
        # Absolute coordinates
        left = data['left'][i]
        top = data['top'][i]
        w = data['width'][i]
        h = data['height'][i]
        
        # Convert to normalized coordinates (0.0 - 1.0) for our OpenCV logic
        norm_x = left / width
        norm_y = top / height
        norm_w = w / width
        norm_h = h / height
        
        results.append({
            "text": text,
            "x": norm_x,
            "y": norm_y,
            "width": norm_w,
            "height": norm_h
        })
        
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps([]))
        sys.exit(0)
    
    image_path = sys.argv[1]
    results = run_tesseract_ocr(image_path)
    print(json.dumps(results, ensure_ascii=False))
