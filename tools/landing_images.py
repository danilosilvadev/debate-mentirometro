"""Gera as variantes otimizadas da landing: python tools/landing_images.py mics.jpg trofeu.jpg"""
import sys
from PIL import Image
OUT = "web/landing/img/"
def make(src, name, widths, jpg_w):
    im = Image.open(src).convert("RGB")
    for w in widths:
        r = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        r.save(f"{OUT}{name}-{w}.webp", "WEBP", quality=78, method=6)
    r = im.resize((jpg_w, round(im.height * jpg_w / im.width)), Image.LANCZOS)
    r.save(f"{OUT}{name}-{jpg_w}.jpg", "JPEG", quality=80, optimize=True, progressive=True)
if __name__ == "__main__":
    make(sys.argv[1], "mics", (640, 1280), 1280)
    make(sys.argv[2], "trofeu", (320, 640), 640)
