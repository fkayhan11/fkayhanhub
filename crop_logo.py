from PIL import Image, ImageChops

def trim(im):
    bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return im

try:
    img = Image.open('portal/logo.png').convert("RGBA")
    # Make background transparent if it's white
    datas = img.getdata()
    new_data = []
    for item in datas:
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
    img.putdata(new_data)
    
    img = trim(img)
    # Upscale nicely
    img = img.resize((img.width * 3, img.height * 3), Image.Resampling.LANCZOS)
    img.save('portal/logo_cropped.png')
    print("Cropped and processed.")
except Exception as e:
    print(f"Error: {e}")
