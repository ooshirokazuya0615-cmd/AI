"""Draw the on-screen layer over rendered frames: the guess-the-song card and the timeline of years.

  each piece: a "?" card for its first notes (guess it!), then it turns into title, composer and year
  bottom:     a timeline 1650-1900; a glowing marker travels to the year of the piece now playing
  start/end:  the series title, and a closing question for the comments

    SONGS_MODULE=songs7 python overlay.py frames_in/ frames_out/ [--fps 30]
"""
import argparse
import importlib
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = importlib.import_module(os.environ.get('SONGS_MODULE', 'songs7'))
FONT_DIR = Path('/usr/share/fonts/truetype/crosextra')
SERIF_B = str(FONT_DIR / 'Caladea-Bold.ttf')
SANS = str(FONT_DIR / 'Carlito-Regular.ttf')
SANS_B = str(FONT_DIR / 'Carlito-Bold.ttf')
Y0, Y1 = 1650, 1900
ERA_COL = {'baroque': (232, 176, 82), 'classical': (120, 200, 255), 'beethoven': (200, 120, 255), 'romantic': (255, 90, 80)}
GUESS = 2.6          # seconds the "?" stays before the answer
SHOW = 3.4           # seconds the answer stays


def smooth(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def font(path, size, cache={}):
    key = (path, size)
    if key not in cache:
        cache[key] = ImageFont.truetype(path, size)
    return cache[key]


def card(draw, W, H, cx, top, lines, alpha, scale=1.0):
    """Rounded translucent card with centred lines [(text, font_path, size, colour)]."""
    if alpha <= 0:
        return
    sizes = [(t, font(fp, int(sz * W / 1920 * scale)), c) for t, fp, sz, c in lines]
    widths = [draw.textbbox((0, 0), t, font=f)[2] for t, f, c in sizes]
    heights = [f.size * 1.25 for t, f, c in sizes]
    pad = int(26 * W / 1920 * scale)
    w, h = max(widths) + 2 * pad, int(sum(heights)) + 2 * pad
    x0, y0 = cx - w // 2, top
    draw.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=int(22 * W / 1920 * scale),
                           fill=(14, 14, 20, int(170 * alpha)), outline=(255, 255, 255, int(60 * alpha)), width=2)
    y = y0 + pad
    for (t, f, c), tw, th in zip(sizes, widths, heights):
        draw.text((cx - tw // 2, y), t, font=f, fill=(*c, int(255 * alpha)))
        y += th


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--fps', type=int, default=30)
    a = ap.parse_args()
    C, _ = S.timeline()
    starts = []
    for s, song in enumerate(S.SONGS):
        hs = [h for h in C if h['s'] == s and h['mech'] != 'bigdrum']
        starts.append((hs[0]['t'], hs[-1]['t'] + hs[-1]['dur'], song))
    t_final = C[-1]['t']
    T_END = S.total_seconds()
    src, dst = Path(a.src), Path(a.dst)
    dst.mkdir(parents=True, exist_ok=True)
    frames = sorted(src.glob('f_*.png'))
    for fpath in frames:
        f = int(fpath.stem.split('_')[1])
        t = (f - 1) / a.fps
        im = Image.open(fpath).convert('RGBA')
        W, H = im.size
        layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        # ---- timeline
        k = min(1.0, t / 1.2) * (1 - smooth((t - (t_final + 1.2)) / 0.8))
        if k > 0:
            bx0, bx1, by = int(W * 0.18), int(W * 0.82), int(H * 0.93)
            d.line((bx0, by, bx1, by), fill=(255, 255, 255, int(110 * k)), width=max(2, W // 640))
            for yr in (1700, 1800, 1900):
                x = bx0 + (bx1 - bx0) * (yr - Y0) / (Y1 - Y0)
                d.line((x, by - H * 0.008, x, by + H * 0.008), fill=(255, 255, 255, int(150 * k)), width=max(1, W // 960))
                tf = font(SANS, int(H * 0.022))
                tw = d.textbbox((0, 0), str(yr), font=tf)[2]
                d.text((x - tw / 2, by + H * 0.012), str(yr), font=tf, fill=(255, 255, 255, int(170 * k)))
            # marker: glides to the current piece's year (during a gap it travels to the next one)
            yr_now, col = starts[0][2]['year'], ERA_COL[starts[0][2]['era']]
            for j, (t0, t1, song) in enumerate(starts):
                if t >= t0:
                    yr_now, col = song['year'], ERA_COL[song['era']]
                    if j + 1 < len(starts) and t > t1:
                        nt0, _, nsong = starts[j + 1]
                        u = smooth((t - t1) / max(0.3, nt0 - t1))
                        yr_now = song['year'] + (nsong['year'] - song['year']) * u
            for j, (t0, t1, song) in enumerate(starts):         # visited years leave a dot
                if t >= t0:
                    x = bx0 + (bx1 - bx0) * (song['year'] - Y0) / (Y1 - Y0)
                    r = H * 0.006
                    d.ellipse((x - r, by - r, x + r, by + r), fill=(*ERA_COL[song['era']], int(200 * k)))
            x = bx0 + (bx1 - bx0) * (yr_now - Y0) / (Y1 - Y0)
            r = H * 0.013
            glow = Image.new('RGBA', im.size, (0, 0, 0, 0))
            ImageDraw.Draw(glow).ellipse((x - 3 * r, by - 3 * r, x + 3 * r, by + 3 * r), fill=(*col, int(150 * k)))
            layer = Image.alpha_composite(layer, glow.filter(ImageFilter.GaussianBlur(r * 1.5)))
            d = ImageDraw.Draw(layer)
            d.ellipse((x - r, by - r, x + r, by + r), fill=(255, 255, 255, int(255 * k)))
            yf = font(SANS_B, int(H * 0.03))
            ys = str(int(round(yr_now)))
            tw = d.textbbox((0, 0), ys, font=yf)[2]
            d.text((x - tw / 2, by - H * 0.06), ys, font=yf, fill=(*col, int(255 * k)))
        # ---- guess card, then the answer
        for t0, t1, song in starts:
            u = t - (t0 - 0.15)
            if 0 <= u < GUESS:
                a_ = smooth(u / 0.25) * (1 - smooth((u - GUESS + 0.2) / 0.2))
                pulse = 1.0 + 0.04 * math.sin(u * 7)
                card(d, W, H, W // 2, int(H * 0.06), [('?', SERIF_B, 92, (255, 255, 255))], a_, pulse)
            elif GUESS <= u < GUESS + SHOW:
                v = u - GUESS
                a_ = smooth(v / 0.25) * (1 - smooth((v - SHOW + 0.4) / 0.4))
                card(d, W, H, W // 2, int(H * 0.06),
                     [(song['title'], SERIF_B, 54, (255, 255, 255)),
                      (f"{song['composer_name']}  ·  {song['year']}", SANS, 34, ERA_COL[song['era']])], a_)
        # ---- series title and closing question
        if t < 3.4:
            a_ = smooth((t - 0.3) / 0.4) * (1 - smooth((t - 3.0) / 0.4))
            tf = font(SERIF_B, int(H * 0.05))
            d.text((W * 0.05, H * 0.80), '300 Years of Music', font=tf, fill=(255, 255, 255, int(230 * a_)))
            d.text((W * 0.05, H * 0.86), 'one marble', font=font(SANS, int(H * 0.032)), fill=(255, 255, 255, int(200 * a_)))
        if t > T_END - 3.2:
            a_ = smooth((t - (T_END - 3.2)) / 0.5)
            card(d, W, H, W // 2, int(H * 0.40), [('How many did you guess?', SERIF_B, 64, (255, 255, 255)),
                                                  ('1680  →  1876', SANS, 36, (255, 210, 140))], a_)
        Image.alpha_composite(im, layer).convert('RGB').save(dst / fpath.name)


if __name__ == '__main__':
    main()
