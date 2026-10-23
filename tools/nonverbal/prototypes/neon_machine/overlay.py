"""Draw the on-screen layer over rendered frames: the guess-the-song quiz and the timeline of years.

  each piece: a quiz card for its first notes: "?", a 3-2-1 countdown and three choices (the other two are
              famous pieces of the same era that are not in the film, so nothing later is given away);
              then the right one lights up with its composer and year
  bottom:     a timeline 1650-1900; a glowing marker travels to the year of the piece now playing
  end:        a closing question for the comments (the title is engraved on the first page, in the scene)

    SONGS_MODULE=songs7 python overlay.py frames_in/ frames_out/ [--fps 30]
"""
import argparse
import importlib
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = importlib.import_module(os.environ.get('SONGS_MODULE', 'songs7'))
FONT_DIR = Path('/usr/share/fonts/truetype/crosextra')
SERIF_B = str(FONT_DIR / 'Caladea-Bold.ttf')
SANS = str(FONT_DIR / 'Carlito-Regular.ttf')
SANS_B = str(FONT_DIR / 'Carlito-Bold.ttf')
CHOICE = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'          # has the check mark
CHOICE_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
Y0, Y1 = 1650, 1900
ERA_COL = {'baroque': (232, 176, 82), 'classical': (120, 200, 255), 'beethoven': (200, 120, 255), 'romantic': (255, 90, 80)}
GUESS = 3.0          # seconds from the first note to the answer (three dots drain, one a second)
SHOW = 3.0           # seconds the answer stays
LEAD = 1.2           # the question is up this long before the first note (from the second piece on)
# the three choices for each piece: (decoys..., with the answer at index ANSWER_AT); all public domain
QUIZ = {
    'canon': ['Air on the G String  (Bach)', None, 'Spring, The Four Seasons  (Vivaldi)'],
    'toc': [None, 'Hallelujah Chorus  (Handel)', 'Winter, The Four Seasons  (Vivaldi)'],
    'tm': ['Surprise Symphony  (Haydn)', 'Symphony No. 40  (Mozart)', None],
    'ekn': ['Queen of the Night  (Mozart)', None, 'Emperor Quartet  (Haydn)'],
    'b5': [None, 'Moonlight Sonata  (Beethoven)', 'Erlkonig  (Schubert)'],
    'fe': ['Ave Maria  (Schubert)', 'Moonlight Sonata  (Beethoven)', None],
    'otj': ['Ave Maria  (Schubert)', None, 'William Tell Overture  (Rossini)'],
    'mk': [None, 'Ride of the Valkyries  (Wagner)', 'Swan Lake  (Tchaikovsky)'],
}


def smooth(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def font(path, size, cache={}):
    key = (path, size)
    if key not in cache:
        cache[key] = ImageFont.truetype(path, size)
    return cache[key]


def card(draw, W, H, cx, top, lines, alpha, scale=1.0, left=False, right_edge=None, centre_first=False):
    """Rounded translucent card with lines [(text, font_path, size, colour[, alpha of the line])], centred,
    or left-aligned (a list of choices; with centre_first, the heading above them stays centred)."""
    if alpha <= 0:
        return
    sizes = [(ln[0], font(ln[1], int(ln[2] * W / 1920 * scale)), ln[3], ln[4] if len(ln) > 4 else 1.0) for ln in lines]
    widths = [draw.textbbox((0, 0), t, font=f)[2] for t, f, c, la in sizes]
    heights = [f.size * 1.25 for t, f, c, la in sizes]
    pad = int(26 * W / 1920 * scale)
    w, h = max(widths) + 2 * pad, int(sum(heights)) + 2 * pad
    x0, y0 = (cx - w // 2, top) if right_edge is None else (right_edge - w, top)
    cx = x0 + w // 2
    draw.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=int(22 * W / 1920 * scale),
                           fill=(14, 14, 20, int(170 * alpha)), outline=(255, 255, 255, int(60 * alpha)), width=2)
    y = y0 + pad
    for j, ((t, f, c, la), tw, th) in enumerate(zip(sizes, widths, heights)):
        x = x0 + pad if left and not (centre_first and j == 0) else cx - tw // 2
        draw.text((x, y), t, font=f, fill=(*c, int(255 * alpha * la)))
        y += th


_VIG, _BAND = {}, {}


def film_finish(im, f):
    """What a real camera adds: a soft vignette, a hint of lateral colour fringing, and fine moving grain."""
    x = np.asarray(im.convert('RGB')).astype(np.float32) / 255.0
    H, W = x.shape[:2]
    if (W, H) not in _VIG:
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        _VIG[(W, H)] = (1.0 - 0.22 * np.clip(r - 0.35, 0, None) ** 1.6)[..., None]
    x = x * _VIG[(W, H)]
    sh = max(1, W // 1280)
    x[:, sh:, 0] = x[:, :-sh, 0]          # red a pixel outward, blue inward: subtle chromatic fringe
    x[:, :-sh, 2] = x[:, sh:, 2]
    g = np.random.default_rng(f).normal(0, 0.012, (H, W, 1)).astype(np.float32)
    x = np.clip(x + g * (0.6 + 0.4 * x), 0, 1)
    return Image.fromarray((x * 255).astype(np.uint8)).convert('RGBA')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--film', action='store_true', help='lens and film finish under the graphics')
    a = ap.parse_args()
    C, _ = S.timeline()
    starts, last_hit = [], []
    for s, song in enumerate(S.SONGS):
        hs = [h for h in C if h['s'] == s and h['mech'] != 'bigdrum']
        starts.append((hs[0]['t'], hs[-1]['t'] + hs[-1]['dur'], song))
        last_hit.append(hs[-1]['t'])
    t_final = C[-1]['t']
    T_END = S.total_seconds()
    src, dst = Path(a.src), Path(a.dst)
    dst.mkdir(parents=True, exist_ok=True)
    frames = sorted(src.glob('f_*.png'))
    for fpath in frames:
        f = int(fpath.stem.split('_')[1])
        t = (f - 1) / a.fps
        im = Image.open(fpath).convert('RGBA')
        if a.film:
            im = film_finish(im, f)
        W, H = im.size
        layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        # ---- timeline, on a soft dark band so it reads on every wall
        k = min(1.0, t / 1.2) * (1 - smooth((t - (t_final + 1.2)) / 0.8))
        if k > 0:
            if (W, H) not in _BAND:
                g_ = np.clip((np.arange(H) / H - 0.80) / 0.20, 0, 1) ** 1.4 * 130
                _BAND[(W, H)] = np.repeat(g_.astype(np.uint8)[:, None], W, axis=1)
            band = Image.new('RGBA', im.size, (8, 6, 12, 0))
            band.putalpha(Image.fromarray((_BAND[(W, H)] * k).astype(np.uint8)))
            layer = Image.alpha_composite(layer, band)
            d = ImageDraw.Draw(layer)
            bx0, bx1, by = int(W * 0.06), int(W * 0.66), int(H * 0.885)    # clear of the player's progress bar
            d.line((bx0, by + 1, bx1, by + 1), fill=(12, 10, 16, int(70 * k)), width=max(2, W // 640) + 2)
            d.line((bx0, by, bx1, by), fill=(255, 255, 255, int(150 * k)), width=max(2, W // 640))
            for yr in (1700, 1800, 1900):
                x = bx0 + (bx1 - bx0) * (yr - Y0) / (Y1 - Y0)
                d.line((x, by - H * 0.008, x, by + H * 0.008), fill=(255, 255, 255, int(150 * k)), width=max(1, W // 960))
                tf = font(SANS, int(H * 0.026))
                tw = d.textbbox((0, 0), str(yr), font=tf)[2]
                d.text((x - tw / 2, by + H * 0.012), str(yr), font=tf, fill=(255, 255, 255, int(190 * k)),
                       stroke_width=max(1, H // 720), stroke_fill=(12, 10, 16, int(110 * k)))
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
            # the year, big, rolling through the decades between pieces; the era under it; a dot per piece,
            # filled in its era's colour once it has been guessed
            # the period named from the year shown (Classical from 1750, Romantic from 1820), so the label
            # changes as the counter crosses the line, not when the next piece starts
            era_now = 'BAROQUE' if yr_now < 1750 else 'CLASSICAL' if yr_now < 1820 else 'ROMANTIC'
            yf = font(SERIF_B, int(H * 0.075))
            ink_ = (12, 10, 16, int(150 * k))
            xb_ = W * 0.968 - H * 0.45                       # bottom right: rows start (clef, first notes) at the left
            d.rounded_rectangle((xb_, by - H * 0.115, xb_ + H * 0.45, by + H * 0.058), radius=int(H * 0.02),
                                fill=(10, 8, 14, int(105 * k)))           # its own plate, over any page
            d.text((xb_ + H * 0.025, by - H * 0.105), str(int(round(yr_now))), font=yf, fill=(*col, int(255 * k)),
                   stroke_width=max(2, H // 300), stroke_fill=ink_)
            d.text((xb_ + H * 0.028, by - H * 0.020), era_now, font=font(SANS_B, int(H * 0.024)),
                   fill=(255, 255, 255, int(220 * k)), stroke_width=max(1, H // 540), stroke_fill=ink_)
            r = H * 0.013
            for j, (t0, t1, song) in enumerate(starts):
                x = xb_ + H * 0.028 + r + j * r * 2.9
                yv = by + H * 0.031
                if t >= t0 + GUESS:
                    d.ellipse((x - r, yv - r, x + r, yv + r), fill=(*ERA_COL[song['era']], int(255 * k)))
                else:
                    d.ellipse((x - r, yv - r, x + r, yv + r), outline=(255, 255, 255, int(150 * k)), width=max(1, W // 960))
        # ---- the quiz: a question with three choices and a countdown, then the answer lights up
        for idx, (t0, t1, song) in enumerate(starts):
            lead = 0.15 if idx == 0 else LEAD
            u = t - t0                                    # 0 at the first note; the countdown runs from there
            # the answer leaves with the piece's last note: the marble exits top right, where the card is
            end = min(GUESS + SHOW, last_hit[idx] - t0 - 0.2)
            if not -lead <= u < end:
                continue
            opts = QUIZ.get(song['key'], [None, None, None])
            right = opts.index(None)
            # every choice in the same form (a title only), so the layout never gives the answer away
            names = [song['title'] if o is None else o.split('  (')[0] for o in opts]
            col = ERA_COL[song['era']]
            a_ = smooth((u + lead) / 0.25) * (1 - smooth((u - end + 0.4) / 0.4))
            if u < GUESS:
                n_left = 3 - int(max(0.0, u) / (GUESS / 3))                 # 3, 2, 1 dots
                lines = [(f'{idx + 1}/{len(starts)}     ' + '●' * n_left + '○' * (3 - n_left), CHOICE_B, 40, (255, 255, 255))]
                lines += [(f'{"ABC"[k]}   {names[k]}', CHOICE, 44, (240, 240, 244)) for k in range(3)]
            else:
                v = u - GUESS
                lines = [(f'✓  {"ABC"[right]}   {song["title"]}', CHOICE_B, 48, col),    # (DejaVu has the tick)
                         (f"{song['composer_name']}  ·  {song.get('year_label', song['year'])}", SANS_B, 40, col,
                          smooth((v - 0.15) / 0.3))]
            pop = 1.0 + (0.12 * math.sin(math.pi * min(1.0, (u - GUESS) / 0.35)) if u >= GUESS else 0.0)  # the reveal pops
            card(d, W, H, W // 2, int(H * 0.04), lines, a_, pop, left=True, right_edge=int(W * 0.97),
                 centre_first=u >= GUESS)                                   # top right, clear of the marble
        # ---- closing question
        if t > T_END - 3.2:
            a_ = smooth((t - (T_END - 3.2)) / 0.5)
            card(d, W, H, W // 2, int(H * 0.40), [('How many did you guess?', SERIF_B, 64, (255, 255, 255)),
                                                  ('1680  →  1876', SANS, 36, (255, 210, 140))], a_)
        Image.alpha_composite(im, layer).convert('RGB').save(dst / fpath.name)


if __name__ == '__main__':
    main()
