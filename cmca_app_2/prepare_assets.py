from PIL import Image, ImageOps
from pathlib import Path

src = Path("website_images/CMCA_Images.tif")
dst_color = Path("website_images/CMCA_Images_hero_color.jpg")
dst_gray = Path("website_images/CMCA_Images_hero_gray.jpg")

if not src.exists():
    print(f"❌ Source not found: {src}")
else:
    # Open original and save color version 
    im = Image.open(src).convert("RGB")
    im.save(dst_color, "JPEG", quality=95)
    print(f"✅ Saved color version: {dst_color}")

    # Convert to grayscale and save 
    gray = ImageOps.grayscale(im)
    gray = gray.convert("RGB")  # ensure 3 channels for web
    gray.save(dst_gray, "JPEG", quality=95)
    print(f"✅ Saved gray version: {dst_gray}")



