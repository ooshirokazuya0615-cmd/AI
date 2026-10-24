import time, numpy as np
from voices import VOICES
from prosody import EMOTIONS
for name, cls in VOICES.items():
    v = cls()
    for e in EMOTIONS:
        rng = np.random.default_rng(100)
        t0 = time.time()
        p = v.plan(e, rng)
        x = v.render(p, rng)
        print(f"{name:9s} {e:10s} len={len(x)/48000:.2f}s nsyl={len(p.syls)} peak={np.abs(x).max():.3g} rms={np.sqrt(np.mean(x**2)):.3g} nan={np.isnan(x).any()} {time.time()-t0:.2f}s")
