"""Thumbnails in the "songs you know but not the name" look: a clean render below, the top of the frame washed
to white, and two lines of tall condensed black type across it (no box, no outline), as those channels do it.
usage: thumb_band.py src.png out.jpg FONT.ttf "LINE ONE" "LINE TWO" [band fraction, default 0.40]
(FONT: fonts/Anton-Regular.ttf, SIL Open Font License, beside this script)
The render comes from film8.py with THUMB_CAM="frame:zoom:dx:dz" (the subject framed low) and --stills."""
import sys
from PIL import Image, ImageDraw, ImageEnhance, ImageFont
import numpy as np

src, out, font, l1, l2 = sys.argv[1:6]
band = float(sys.argv[6]) if len(sys.argv) > 6 else 0.40
W, H = 1280, 720
im = Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS)
im = ImageEnhance.Contrast(im).enhance(1.10)
im = ImageEnhance.Color(im).enhance(1.20)
im = ImageEnhance.Sharpness(im).enhance(1.3)
# the wash: white over the band, easing into the picture below it so there is no hard edge
y = np.arange(H, dtype=np.float32)[:, None, None] / H
w = np.clip((band + 0.10 - y) / 0.12, 0.0, 1.0) ** 1.5
a = np.asarray(im).astype(np.float32)
im = Image.fromarray(np.clip(a * (1 - w) + 250.0 * w, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(im)


def fit(text, max_w, max_h):
    s = max_h
    while s > 20:
        f = ImageFont.truetype(font, s)
        x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
        if x1 - x0 <= max_w:
            return f
        s -= 2
    return ImageFont.truetype(font, s)


f1 = fit(l1, int(W * 0.90), int(H * band * 0.52))
f2 = fit(l2, int(W * 0.90), f1.size)
top = int(H * 0.035)
for text, f in ((l1, f1), (l2, f2)):
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
    d.text(((W - (x1 - x0)) // 2 - x0, top - y0), text, font=f, fill=(17, 17, 17))
    top += int((y1 - y0) * 1.16)
im.save(out, quality=95)
print('wrote', out)
