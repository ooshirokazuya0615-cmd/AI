"""Thumbnails: a clean render (no overlay), a gentle lift and vignette, and two lines of big type.
usage: thumb_compose.py src.png out.jpg "LINE ONE" "LINE TWO" [left|right|bottom] [accent hex]
The renders come from film8.py with THUMB_CAM="frame:zoom:dx:dz;..." and --stills (motion blur off)."""
import sys
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
import numpy as np

src, out, l1, l2 = sys.argv[1:5]
side = sys.argv[5] if len(sys.argv) > 5 else 'left'
accent = tuple(int(sys.argv[6][i:i + 2], 16) for i in (0, 2, 4)) if len(sys.argv) > 6 else (255, 214, 64)
W, H = 1280, 720
im = Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS)
im = ImageEnhance.Contrast(im).enhance(1.12)
im = ImageEnhance.Color(im).enhance(1.18)
im = ImageEnhance.Sharpness(im).enhance(1.3)
# a vignette that darkens the corner the text sits in, so the type always reads
yy, xx = np.mgrid[0:H, 0:W]
cx = 0.82 * W if side == 'right' else 0.18 * W
cy = 0.8 * H if side == 'bottom' else 0.2 * H
d = np.sqrt(((xx - cx) / W) ** 2 + ((yy - cy) / H) ** 2)
shade = np.clip(1.0 - 0.55 * np.exp(-(d / 0.42) ** 2), 0.45, 1.0)
edge = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
shade *= np.clip(1.08 - 0.22 * edge ** 2, 0.7, 1.0)
a = np.asarray(im).astype(np.float32) * shade[..., None]
im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
BLACK = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
try:
    ImageFont.truetype(BLACK, 10)
except OSError:
    import glob
    BLACK = (glob.glob('/usr/share/fonts/**/Inter*Black*.tt[fc]', recursive=True)
             + glob.glob('/usr/share/fonts/**/Inter*.tt[fc]', recursive=True))[0]


def fit(text, max_w, start):
    s = start
    while s > 20:
        f = ImageFont.truetype(BLACK, s)
        if ImageDraw.Draw(im).textbbox((0, 0), text, font=f)[2] <= max_w:
            return f
        s -= 4
    return ImageFont.truetype(BLACK, s)


layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
dr = ImageDraw.Draw(layer)
f1, f2 = fit(l1, int(W * 0.50), 132), fit(l2, int(W * 0.50), 150)
x0 = None if side == 'right' else int(W * 0.045)
y = int(H * 0.06) if side != 'bottom' else int(H * 0.94 - (f1.size + f2.size) * 1.02)
for text, f, col in ((l1, f1, (255, 255, 255)), (l2, f2, accent)):
    tw = dr.textbbox((0, 0), text, font=f)[2]
    x = int(W * 0.955) - tw if side == 'right' else x0
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))   # a soft drop shadow
    ImageDraw.Draw(sh).text((x + 6, y + 8), text, font=f, fill=(0, 0, 0, 200))
    layer = Image.alpha_composite(layer, sh.filter(ImageFilter.GaussianBlur(7)))
    dr = ImageDraw.Draw(layer)
    dr.text((x, y), text, font=f, fill=(*col, 255), stroke_width=7, stroke_fill=(10, 8, 14, 255))
    y += int(f.size * 1.02)
Image.alpha_composite(im.convert('RGBA'), layer).convert('RGB').save(out, quality=95)
print('wrote', out)
