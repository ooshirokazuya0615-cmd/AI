"""A/B: does moving a low/dark voice's energy above the phone cut restore pitch survival?"""
import json, numpy as np
from pathlib import Path
from voices import Babble, Iron, Creature
from prosody import EMO
from dsp import SR, phone_sim, pitch_survival, write_wav
from make_all import limiter, window_end
ROOT = Path(__file__).resolve().parent.parent
res = {}
def run(tag, cls, emo, seeds, base=None, tilt_override=None, fscale=None):
    out = []
    for s in seeds:
        v = cls()
        if base: v.base_hz = base
        if fscale: v.fscale = fscale
        rng = np.random.default_rng(s)
        p = v.plan(emo, rng)
        if tilt_override is not None:
            p.params = dict(p.params, tilt=tilt_override)
        x = v.render(p, rng)[:window_end(p)]
        x = limiter(x / np.percentile(np.abs(x), 99.9) * 0.5)
        r = pitch_survival(x, phone_sim(x), v.base_hz)
        out.append(r)
        if s == seeds[0]:
            write_wav(ROOT / 'wav' / f'phonefix_{tag}.wav', x)
    keys = out[0].keys()
    res[tag] = {k: round(float(np.mean([o.get(k, np.nan) for o in out])), 3) for k in keys}
    print(tag, res[tag], flush=True)
seeds = [1000 + i for i in range(6)]
run('babble_sad_default_f0_270Hz', Babble, 'sad', seeds)
run('babble_sad_fix_base400_tilt0.1', Babble, 'sad', seeds, base=400, tilt_override=0.1)
run('creature_sad_default', Creature, 'sad', seeds)
run('creature_sad_fix_base680', Creature, 'sad', seeds, base=680)
run('iron_angry_default_f0_147', Iron, 'angry', seeds[:3])
run('iron_angry_fix_base220', Iron, 'angry', seeds[:3], base=220)
json.dump(res, open(ROOT / 'phonefix.json', 'w'), indent=1)
