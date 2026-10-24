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
ERA_COL = {'baroque': (232, 176, 82), 'classical': (120, 200, 255), 'romantic': (255, 90, 80)}
# each piece's colour (the marble's, as in film8.PIECE_COL), for the closing recap
PIECE_RGB = {'canon': (60, 120, 255), 'toc': (20, 190, 110), 'tm': (150, 70, 220), 'ekn': (255, 190, 50),
             'b5': (255, 120, 40), 'fe': (190, 255, 70), 'otj': (30, 150, 170), 'mk': (60, 220, 255)}


def era_of(year):
    """The period as the year plate names it (Classical from 1750, Romantic from 1820), so its colour, its
    label and the dots always agree (the Fifth, 1808, is Classical: blue, like its label)."""
    return 'baroque' if year < 1750 else 'classical' if year < 1820 else 'romantic'
GUESS = 3.0          # seconds from the first note to the answer (three dots drain, one a second)
SHOW = 3.0           # seconds the answer stays
LEAD = 1.2           # the question is up this long before the first note (from the second piece on)
# the three choices for each piece: (decoys..., with the answer at index ANSWER_AT); all public domain
QUIZ = {
    'canon': ['Air on the G String  (Bach)', None, 'Spring, The Four Seasons  (Vivaldi)'],
    'toc': [None, 'Hallelujah Chorus  (Handel)', 'Winter, The Four Seasons  (Vivaldi)'],
    'tm': ['Surprise Symphony  (Haydn)', 'Symphony No. 40  (Mozart)', None],
    'ekn': ['Queen of the Night  (Mozart)', None, 'Emperor Quartet  (Haydn)'],
    'b5': [None, 'Moonlight Sonata  (Beethoven)', 'Erlkönig  (Schubert)'],
    'fe': ['Ave Maria  (Schubert)', 'Nocturne Op. 9 No. 2  (Chopin)', None],
    'otj': ['Wedding March  (Mendelssohn)', None, 'William Tell Overture  (Rossini)'],
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
        k = smooth((t - 2.3) / 0.6) * (1 - smooth((t - (t_final - 0.9)) / 0.5))   # in once the opening has settled,
        #                                                                       out before the drum landing
        if k > 0:
            if (W, H) not in _BAND:
                g_ = np.clip((np.arange(H) / H - 0.78) / 0.16, 0, 1) ** 1.2 * 178
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
            yr_now = starts[0][2]['year']
            for j, (t0, t1, song) in enumerate(starts):
                if t >= t0:
                    yr_now = song['year']
                    if j + 1 < len(starts) and t > t1:
                        nt0, _, nsong = starts[j + 1]
                        u = smooth((t - t1) / max(0.3, nt0 - t1))
                        yr_now = song['year'] + (nsong['year'] - song['year']) * u
            col = ERA_COL[era_of(yr_now)]
            for j, (t0, t1, song) in enumerate(starts):         # visited years leave a dot
                if t >= t0:
                    x = bx0 + (bx1 - bx0) * (song['year'] - Y0) / (Y1 - Y0)
                    r = H * 0.006
                    d.ellipse((x - r, by - r, x + r, by + r), fill=(*ERA_COL[era_of(song['year'])], int(200 * k)))
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
            era_now = era_of(yr_now).upper()
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
                    d.ellipse((x - r, yv - r, x + r, yv + r), fill=(*ERA_COL[era_of(song['year'])], int(255 * k)))
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
            col = ERA_COL[era_of(song['year'])]
            a_ = smooth((u + lead) / 0.25) * (1 - smooth((u - end + 0.4) / 0.4))
            if u < GUESS:
                n_left = 3 - int(max(0.0, u) / (GUESS / 3))                 # 3, 2, 1 dots
                # "6 of 8", not "6/8": over a staff a slash reads as a time signature
                lines = [(f'{idx + 1} of {len(starts)}     ' + '●' * n_left + '○' * (3 - n_left), CHOICE_B, 40, (255, 255, 255))]
                lines += [(f'{"ABC"[k]}   {names[k]}', CHOICE, 44, (240, 240, 244)) for k in range(3)]
            else:
                v = u - GUESS
                lines = [(f'✓  {"ABC"[right]}   {song["title"]}', CHOICE_B, 48, col),    # (DejaVu has the tick)
                         (f"{song['composer_name']}  ·  {song.get('year_label', song['year'])}", SANS_B, 40, col,
                          smooth((v - 0.15) / 0.3))]
                if idx == len(starts) - 1:                 # the last answer: keep them to the end
                    lines.append(('Keep count: your rank is at the end', SANS_B, 34, (255, 255, 255), smooth((v - 0.6) / 0.4)))
            pop = 1.0 + (0.12 * math.sin(math.pi * min(1.0, (u - GUESS) / 0.35)) if u >= GUESS else 0.0)  # the reveal pops
            card(d, W, H, W // 2, int(H * 0.04), lines, a_, pop, left=True, right_edge=int(W * 0.97),
                 centre_first=u >= GUESS)                                   # top right, clear of the marble
        # ---- the opening promise, for viewers who meet it muted in the feed
        if t < 2.6:
            a_ = smooth((t - 0.25) / 0.3) * (1 - smooth((t - 2.15) / 0.35))
            if a_ > 0:
                xc_, ys_ = W * 0.70, (H * 0.31, H * 0.385)
                lines_ = (('8 pieces  ·  300 years', font(SANS_B, int(H * 0.050)), (255, 250, 240)),
                          ('can you name them all?', font(SANS_B, int(H * 0.062)), (255, 214, 140)))
                bw_ = max(d.textbbox((0, 0), t_, font=f_)[2] for t_, f_, _ in lines_)
                d.rounded_rectangle((xc_ - bw_ / 2 - H * 0.03, ys_[0] - H * 0.022, xc_ + bw_ / 2 + H * 0.03,
                                     ys_[1] + H * 0.085), radius=int(H * 0.025), fill=(12, 10, 16, int(110 * a_)))
                for (t_, f_, c_), y_ in zip(lines_, ys_):
                    tw = d.textbbox((0, 0), t_, font=f_)[2]
                    d.text((xc_ - tw / 2, y_), t_, font=f_, fill=(*c_, int(245 * a_)),
                           stroke_width=max(2, H // 300), stroke_fill=(12, 10, 16, int(170 * a_)))
        # ---- the rise back through the pages: the year of the page in view, stepping back to the start
        FIN = S.FINALE
        r0_, r1_ = t_final + FIN['rise0'], t_final + FIN['rise1']
        if r0_ - 0.4 <= t <= r1_ + 0.6:
            n_ = len(starts) - 1
            i_ = min(n_, max(0, int(math.floor((t - r0_) / (r1_ - r0_) * n_ + 0.2))))   # the page the camera is on
            sg_ = starts[n_ - i_][2]
            a_ = smooth((t - (r0_ - 0.4)) / 0.4) * (1 - smooth((t - r1_) / 0.6))
            yf_ = font(SERIF_B, int(H * 0.085))
            lbl = str(sg_.get('year_label', sg_['year']))
            tw = d.textbbox((0, 0), lbl, font=yf_)[2]
            col_ = ERA_COL[era_of(sg_['year'])]
            d.text((W * 0.95 - tw, H * 0.80), lbl, font=yf_, fill=(*col_, int(255 * a_)),
                   stroke_width=max(2, H // 300), stroke_fill=(12, 10, 16, int(160 * a_)))
        # ---- closing card: in the open gallery right of the wall, held to the end
        t_card = t_final + FIN['card']
        if t > t_card - 0.1:
            a_ = smooth((t - t_card) / 0.6)
            x0_, x1_, y_ = W * 0.575, W * 0.965, H * 0.085
            d.rounded_rectangle((x0_, y_ - H * 0.03, x1_, y_ + H * 0.645), radius=int(H * 0.025),   # below it: room for
                                #                                                                the end screen
                                fill=(14, 12, 20, int(165 * a_)), outline=(255, 255, 255, int(50 * a_)), width=2)
            cx_ = (x0_ + x1_) / 2

            def line(txt, path, frac, colr, yy, centre=True, x=None):
                f_ = font(path, int(H * frac))
                tw_ = d.textbbox((0, 0), txt, font=f_)[2]
                d.text((cx_ - tw_ / 2 if centre else x, yy), txt, font=f_, fill=(*colr, int(255 * a_)))
                return yy + H * frac * 1.32
            y_ = line('How many did you guess?', SERIF_B, 0.060, (255, 255, 255), y_)
            y_ += H * 0.012
            for k_, (t0_, t1_, sg_) in enumerate(starts):        # the eight answers, in the marble's colours
                r_ = H * 0.011
                xd_ = x0_ + W * 0.03
                d.ellipse((xd_ - r_, y_ + H * 0.019 - r_, xd_ + r_, y_ + H * 0.019 + r_), fill=(*PIECE_RGB[sg_['key']], int(255 * a_)))
                txt_ = f"{sg_.get('year_label', sg_['year'])}   {sg_['title']}"
                y_ = line(txt_, SANS, 0.032, (236, 236, 242), y_, centre=False, x=xd_ + W * 0.016)
            y_ += H * 0.018
            y_ = line('8  Maestro   ·   6–7  Virtuoso', SANS_B, 0.038, (255, 214, 140), y_)
            y_ = line('4–5  Apprentice   ·   0–3  Listener', SANS_B, 0.038, (255, 214, 140), y_)
            y_ += H * 0.014
            line('Comment your rank  ↓', CHOICE_B, 0.044, (255, 255, 255), y_)
        Image.alpha_composite(im, layer).convert('RGB').save(dst / fpath.name)


if __name__ == '__main__':
    main()
