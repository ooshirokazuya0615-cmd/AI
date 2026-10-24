"""Quick PIL contact sheet of a sim run (debug only, not the real renderer)."""
import sys
import numpy as np
from PIL import Image, ImageDraw
import sim

S = 0.4
W, H = int(1200 * S), int(2000 * S)
OX, OY = 600, 250  # world (0,0) at (OX*S, OY*S) from top-left


def P(x, y):
    return ((x + OX) * S, (OY - y) * S)


def body_lines(b):
    """Segments (a,b,r) for one recorded pose row."""
    out = []
    for k, name in enumerate(sim.BODY_ORDER):
        x, y, a = b[k]
        if name == 'head':
            out.append(('head', (x, y), sim.HEAD_R))
            continue
        L, r, _ = sim.SEGS[name]
        d = np.array([np.cos(a), np.sin(a)]) * L / 2
        out.append((name, (x - d[0], y - d[1]), (x + d[0], y + d[1]), r))
    return out


def draw_course(dr):
    dr.rectangle([P(-1400, 0), P(sim.LEDGE_X1, -sim.RISE * 1.6)], fill=(200, 160, 110))
    for i in range(sim.STEPS):
        x0 = sim.LEDGE_X1 + sim.TREAD * i
        yt = -sim.RISE * (i + 1)
        dr.rectangle([P(x0, yt), P(x0 + sim.TREAD, yt - sim.RISE * 1.4)], fill=(200, 160, 110))
    for x, y in sim.PEGS:
        a, b = P(x - sim.PEG_R, y + sim.PEG_R), P(x + sim.PEG_R, y - sim.PEG_R)
        dr.ellipse([a, b], fill=(120, 130, 150))
    dr.line([P(*sim.PLATE[0]), P(*sim.PLATE[1])], fill=(120, 130, 150), width=6)
    dr.line([P(-sim.WALL_X, -380), P(-sim.WALL_X, sim.FLOOR_Y)], fill=(90, 90, 90), width=4)
    dr.line([P(sim.WALL_X, -160), P(sim.WALL_X, sim.FLOOR_Y)], fill=(90, 90, 90), width=4)


def sheet(rec, out, every=0.2):
    img = Image.new('RGB', (W, H), (245, 240, 230))
    dr = ImageDraw.Draw(img)
    draw_course(dr)
    py = rec.pad[-1, 0]
    dr.rectangle([P(-sim.PAD_W / 2, sim.PAD_TOP_REST), P(sim.PAD_W / 2, sim.PAD_TOP_REST - sim.PAD_H)], outline=(230, 80, 70), width=2)
    n = rec.steps
    idx = list(range(0, n, int(every / sim.DT))) + [n - 1]
    for j, i in enumerate(idx):
        c = j / max(len(idx) - 1, 1)
        col = (int(30 + 200 * c), int(60 + 40 * (1 - c)), int(200 * (1 - c)))
        for seg in body_lines(rec.bodies[i]):
            if seg[0] == 'head':
                (x, y), r = seg[1], seg[2]
                dr.ellipse([P(x - r, y + r), P(x + r, y - r)], outline=col, width=2)
            else:
                dr.line([P(*seg[1]), P(*seg[2])], fill=col, width=3)
        bx, by = rec.ball[i, :2]
        dr.ellipse([P(bx - 31, by + 31), P(bx + 31, by - 31)], outline=(20, 150, 140), width=1)
    tr = [P(*rec.bodies[i, 0, :2]) for i in range(0, n, 10)]
    dr.line(tr, fill=(0, 0, 0), width=1)
    for e in rec.events:
        if e['other'] == 'body':
            x, y = P(e['x'], e['y'])
            r = 1 + min(e['J'] / 800, 5)
            dr.ellipse([x - r, y - r, x + r, y + r], outline=(255, 0, 0))
    img.save(out)


if __name__ == '__main__':
    kw = dict(a.split('=') for a in sys.argv[2:])
    kw = {k: (int(v) if k == 'seed' else float(v)) for k, v in kw.items()}
    rec = sim.simulate(sim.Params(**kw))
    print(sim.evaluate(rec))
    sheet(rec, sys.argv[1])
