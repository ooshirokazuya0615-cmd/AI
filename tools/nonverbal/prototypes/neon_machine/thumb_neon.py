"""Thumbnails with neon words over a dark render: each line a coloured tube with a white-hot core and a wide
soft glow (cyan above, pink below), the way the neon marble-music thumbnails are lettered.
usage: thumb_neon.py src.png out.jpg "LINE ONE" "LINE TWO" u v h
u, v place the centre of the words (-1..1 from the frame's centre, v up); h is the cap height of the lower line
as a fraction of the frame (the upper line is 0.8 of it). The render comes from film8.py with THUMB_TEXT='[]'
(no depth of field) and THUMB_CAM, --stills."""
import sys
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

src, out, l1, l2 = sys.argv[1:5]
u, v, h = (float(x) for x in sys.argv[5:8])
W, H = 1280, 720
FONT = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
CYAN, PINK = (70, 225, 255), (255, 60, 170)
im = Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS)
im = ImageEnhance.Contrast(im).enhance(1.08)
im = ImageEnhance.Color(im).enhance(1.15)
im = ImageEnhance.Sharpness(im).enhance(1.3)


def font_for(cap):                               # the size whose capital letters are `cap` pixels tall
    s = int(cap * 1.4)
    while s > 10:
        f = ImageFont.truetype(FONT, s)
        if f.getbbox('H')[3] - f.getbbox('H')[1] <= cap:
            return f
        s -= 1
    return ImageFont.truetype(FONT, s)


MAX_W = 0.50 * W                                 # the words keep to their half of the frame
while True:
    lines = [(l1, font_for(0.8 * h * H), CYAN), (l2, font_for(h * H), PINK)]
    boxes = [f.getbbox(t) for t, f, _ in lines]
    if max(b[2] - b[0] for b in boxes) <= MAX_W or h < 0.03:
        break
    h *= 0.96
gap = int(0.35 * h * H)
total = sum(b[3] - b[1] for b in boxes) + gap
cx, cy = (u + 1) / 2 * W, (1 - v) / 2 * H
top = cy - total / 2
glow = Image.new('RGB', (W, H), (0, 0, 0))
tube = Image.new('RGBA', (W, H), (0, 0, 0, 0))
for (t, f, c), b in zip(lines, boxes):
    x, y = cx - (b[2] - b[0]) / 2 - b[0], top - b[1]
    sw = max(2, int(f.size * 0.035))
    g = Image.new('RGB', (W, H), (0, 0, 0))
    ImageDraw.Draw(g).text((x, y), t, font=f, fill=c, stroke_width=sw * 3, stroke_fill=c)
    for r, k in ((int(f.size * 0.55), 0.9), (int(f.size * 0.22), 0.9), (int(f.size * 0.08), 0.7)):
        glow = ImageChops.add(glow, Image.eval(g.filter(ImageFilter.GaussianBlur(r)), lambda p, k=k: int(p * k)))
    lit = tuple(int(ch * 0.62 + 255 * 0.38) for ch in c)         # the tube, lit from inside
    ImageDraw.Draw(tube).text((x, y), t, font=f, fill=(*lit, 255), stroke_width=sw, stroke_fill=(*c, 255))
    hot = Image.new('RGBA', (W, H), (0, 0, 0, 0))                # its white-hot core
    ImageDraw.Draw(hot).text((x, y), t, font=f, fill=(255, 255, 255, 150))
    hot = hot.filter(ImageFilter.GaussianBlur(max(1, sw)))
    tube = Image.alpha_composite(tube, hot)
    top += (b[3] - b[1]) + gap
im = ImageChops.screen(im, glow)
im = Image.alpha_composite(im.convert('RGBA'), tube).convert('RGB')
im.save(out, quality=95)
print('wrote', out)
