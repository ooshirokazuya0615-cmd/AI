"""
Procedural ASMR foley prototypes (numpy only, 48 kHz, no samples).

Every generator returns (mono float array, info dict).  All randomness is seeded and
every *event* re-draws its own parameters (contact point, speed, sizes) so no two
hits are identical — the "machine-gun" repetition is the #1 tell of cheap foley.

Physical models used
  wood_tap      orthotropic plate modes of a small box lid + Hunt-Crossley nail contact
  glass_tap     wine-glass (m,0) shell modes as split doublets + steel-spoon contact
  crunch        1-D local-load-sharing fiber-bundle fracture (avalanches) -> crack clicks
                filtered by heavily damped chip-fragment modes
  fire_crackle  Hawkes (self-exciting) pop process + Pareto amplitudes + hiss + roar
  slime_squish  cavity (Helmholtz) pops with rising pitch + film-rupture clicks +
                granular time-varying 'squelch' formant noise
  water_drops   van den Doel bubble model (Minnaert f0=3/r, d=0.13/r+0.0072 r^-1.5,
                rising pitch sigma = xi*d) + impact splash + bowl modes
  glass_shatter fracture burst + power-law fragment sizes, plate modes per shard,
                ballistic bounces with restitution, floor contact clicks
  sand_cut      dense stick-slip granular friction driven by knife speed + slab topple
"""
import numpy as np

from dsp import (SR, TAU, damped_sines, fade, filt, fftconv, modal_impact, onepole_lp,
                 place, rng_of, white, colored)


# =========================================================== helpers

def _loss_decay(f, eta):
    """amplitude decay rate (1/s) for loss factor eta: delta = pi f eta ; T60 = 2.2/(f eta)"""
    return np.pi * np.asarray(f) * eta


def crack_burst(rng, dur_ms=0.15, hp=1500, lp=16000):
    """A crack/rupture emission: a few tens of microseconds of broadband noise with an
    asymmetric (instant rise, fast exponential fall) envelope."""
    n = max(4, int(dur_ms * 1e-3 * SR * 3))
    t = np.arange(n) / SR
    x = rng.standard_normal(n) * np.exp(-t / (dur_ms * 1e-3))
    x[0] += 2.0 * np.sign(rng.standard_normal())  # the step-like leading edge
    return filt(x, ('hp', hp, 0.6), ('lp', lp, 0.6), tail=0.01)


# =========================================================== 1. wood tap

def wood_box_modes(lx=0.16, ly=0.11, h=0.005, Ex=11e9, Ey=0.9e9, rho=640, fmax=18000):
    """Simply-supported orthotropic plate (lid of a small hardwood box).
    f_mn = (pi/2)/sqrt(rho h) * sqrt(Dx (m/lx)^4 + 2H (m/lx)^2 (n/ly)^2 + Dy (n/ly)^4)"""
    nu = 0.3
    Dx = Ex * h ** 3 / (12 * (1 - nu ** 2)); Dy = Ey * h ** 3 / (12 * (1 - nu ** 2))
    H = np.sqrt(Dx * Dy)
    modes = []
    for m in range(1, 40):
        for n in range(1, 40):
            f = (np.pi / 2) / np.sqrt(rho * h) * np.sqrt(
                Dx * (m / lx) ** 4 + 2 * H * (m / lx) ** 2 * (n / ly) ** 2 + Dy * (n / ly) ** 4)
            if f < fmax:
                modes.append((f, m, n))
    modes.sort()
    return modes


def wood_tap(seconds=6.0, seed=1, n_taps=None, pattern=None):
    """Fingernail tapping on a small walnut box. Returns mono."""
    rng = rng_of(seed)
    modes = wood_box_modes()
    f = np.array([m[0] for m in modes])
    mi = np.array([m[1] for m in modes]); ni = np.array([m[2] for m in modes])
    # add the enclosed air cavity's first axial modes (box 0.16 x 0.11 x 0.06 m)
    cav = np.array([343 / (2 * 0.16), 343 / (2 * 0.11), 343 / (2 * 0.16) * 2])
    # loss factor: wood ~0.008-0.012 internal + radiation/joint losses rising with f
    eta = 0.020 + 0.006 * (f / 4000)  # internal ~0.01 + joints/table/hand contact
    dec = _loss_decay(f, eta)
    out = np.zeros(int(seconds * SR))
    if pattern is None:  # a human-ish rhythmic pattern: groups of 2-5 taps, drifting tempo
        times, t = [], 0.35
        while t < seconds - 0.6:
            k = rng.integers(2, 6)
            ioi = rng.uniform(0.09, 0.16)
            for j in range(k):
                times.append(t + j * ioi + rng.normal(0, 0.006))
            t += k * ioi + rng.uniform(0.35, 0.8)
        pattern = times[:n_taps] if n_taps else times
    infos = []
    for at in pattern:
        # random tap point on the lid -> mode shape gains
        px, py = rng.uniform(0.25, 0.75), rng.uniform(0.25, 0.75)
        g = np.sin(mi * np.pi * px) * np.sin(ni * np.pi * py)
        g *= rng.uniform(0.85, 1.15, len(g))  # wood grain irregularity
        ff = f * (1 + rng.normal(0, 0.002, len(f)))  # tiny detune per hit (contact changes boundary)
        v0 = rng.uniform(0.25, 0.6)
        rad = np.minimum(ff / 2000, 1.5) * (ff / 1000) ** 0.3
        # two-stage fingernail: the keratin tip (0.3 g, stiff, tiny radius) hits first and
        # gives a ~0.05 ms click; the fingertip pulp (4 g, soft) follows with a ~0.4 ms push.
        y1, info = modal_impact(ff, dec, g, v0=v0, m_hammer=0.0003, k=4e8, lam=0.2, seconds=0.7,
                                rad=rad, mode_mass=0.02, os=16, hammer_click=0.6)
        y2, info2 = modal_impact(ff, dec, g, v0=v0 * 0.8, m_hammer=0.004, k=3e7, lam=0.4, seconds=0.7,
                                 rad=rad, mode_mass=0.02, os=8, hammer_click=0.1)
        lag = int(rng.uniform(0.00015, 0.0004) * SR)
        y = y1 / (np.max(np.abs(y1)) + 1e-12) * 0.9
        y[lag:] += 0.6 * (y2 / (np.max(np.abs(y2)) + 1e-12))[:len(y) - lag]
        info['contact2_ms'] = info2['contact_ms']
        # the cavity coupling: weak, slower decaying 'tok' body
        body = damped_sines(cav, [60, 70, 90], [0.25, 0.15, 0.08], 0.7, phases=[0, 0, 0])
        body = body[:len(y)]
        y = y / (np.max(np.abs(y)) + 1e-12) + 0.35 * body * v0 / 0.6
        place(out, at, y * (v0 / 0.6) ** 1.3)
        infos.append(info)
    # box sits on a table: the table top reflection (path difference ~ 20 cm => 0.58 ms)
    out = out + 0.35 * np.r_[np.zeros(int(0.00058 * SR)), filt(out, ('lp', 6000))][:len(out)]
    c = [i['contact_ms'] for i in infos]
    return fade(out), {'taps': len(pattern), 'contact_ms_med': float(np.median(c)),
                       'n_modes': int(len(f)), 'f_lowest': [round(x) for x in f[:6]]}


# =========================================================== 2. glass tap

def glass_modes(f2=820.0, n=7):
    """(m,0) modes of a wine glass bowl. French (1983): f_m ~ m(m^2-1)/sqrt(m^2+1) scaled
    (bell-shaped bowls are a bit compressed relative to the cylinder law -> exponent 0.9)."""
    m = np.arange(2, 2 + n)
    law = m * (m ** 2 - 1) / np.sqrt(m ** 2 + 1)
    return f2 * (law / law[0]) ** 0.9


def glass_tap(seconds=7.0, seed=2, taps=None):
    """Steel teaspoon tapping a wine glass rim (with a clink of two glasses at the end)."""
    rng = rng_of(seed)
    out = np.zeros(int(seconds * SR))
    taps = taps or [0.3, 1.6, 2.15, 2.5, 4.2]
    f_main = glass_modes(rng.uniform(780, 860))
    for k, at in enumerate(taps):
        # each (m,0) mode is a doublet split by 0.05-0.3 % (glass asymmetry) -> slow beating
        split = 1 + rng.uniform(0.0005, 0.003, len(f_main))
        ff = np.concatenate([f_main, f_main * split])
        theta = rng.uniform(0, np.pi)  # strike angle vs doublet orientation
        mm = np.arange(2, 2 + len(f_main))
        g = np.concatenate([np.cos(mm * theta), np.sin(mm * theta)]) * np.concatenate([1 / mm ** 0.7] * 2)
        eta = np.concatenate([0.0007 * (1 + f_main / 3000)] * 2)  # T60(820 Hz) ~ 3.5 s
        dec = _loss_decay(ff, eta)
        v0 = rng.uniform(0.2, 0.45)
        y, info = modal_impact(ff, dec, g, v0=v0, m_hammer=0.012, k=1.2e9, lam=0.05, seconds=seconds - at,
                               rad=(ff / 1000) ** 0.5, mode_mass=0.03, os=16, hammer_click=0.05)
        # the spoon's own ring (held loosely in fingers -> damped)
        spoon = damped_sines([3150, 5420, 8900], [90, 140, 260], [0.03, 0.02, 0.012],
                             0.25, phases=rng.uniform(0, TAU, 3))
        y = y / (np.max(np.abs(y)) + 1e-12)
        y[:len(spoon)] += spoon * (v0 / 0.45)
        place(out, at, y * (v0 / 0.45))
    return fade(out, fout=0.2), {'contact_ms': info['contact_ms'], 'modes_hz': [round(x) for x in f_main]}


# =========================================================== 3. crunch (crisp bite)

def fiber_bundle_1d(n=600, steps=1500, weibull_k=2.5, seed=0):
    """1-D local-load-sharing fiber bundle under increasing strain.
    Returns list of (step, size, energy) avalanches. Broken fibers pass their load to the
    nearest intact neighbours, producing power-law-ish bursts (crackling noise)."""
    rng = rng_of(seed)
    thr = rng.weibull(weibull_k, n)
    extra = np.zeros(n)
    intact = np.ones(n, bool)
    events = []
    for s in range(steps):
        strain = (s + 1) / steps * 1.6
        size = 0; energy = 0.0
        while True:
            load = strain + extra
            br = intact & (load >= thr)
            if not br.any():
                break
            idx = np.where(br)[0]
            for i in idx:
                if not intact[i]:
                    continue
                intact[i] = False
                L = load[i]
                size += 1; energy += L * L
                # pass load to nearest intact neighbours
                l = i - 1
                while l >= 0 and not intact[l]:
                    l -= 1
                r = i + 1
                while r < n and not intact[r]:
                    r += 1
                tgt = [j for j in (l, r) if 0 <= j < n]
                for j in tgt:
                    extra[j] += L / len(tgt)
                extra[i] = 0
            if not intact.any():
                break
        if size:
            events.append((s, size, energy))
        if not intact.any():
            break
    return events


def chip_fragment_ir(rng, n_modes=4):
    """Impulse response of a small chip fragment: high, very damped plate modes
    (starch foam loss factor ~0.08-0.15)."""
    f = np.exp(rng.uniform(np.log(2200), np.log(9000))) * np.array([1, 1.52, 1.94, 2.6])[:n_modes] \
        * rng.uniform(0.95, 1.05, n_modes)
    eta = rng.uniform(0.07, 0.14)
    return damped_sines(f, _loss_decay(f, eta), rng.uniform(0.3, 1, n_modes), 0.02,
                        phases=rng.uniform(0, TAU, n_modes))


def crunch(seconds=6.0, seed=3):
    """Biting a potato chip then chewing it (close air-conducted mic)."""
    rng = rng_of(seed)
    out = np.zeros(int(seconds * SR))
    # (start time, duration, n fibers, gain) : 1 bite + 4 chews with decreasing material
    phases = [(0.4, 0.16, 700, 1.0), (1.25, 0.22, 380, 0.55), (1.75, 0.22, 300, 0.45),
              (2.3, 0.25, 220, 0.35), (2.85, 0.28, 160, 0.28),
              (3.9, 0.15, 650, 0.95), (4.7, 0.22, 330, 0.5), (5.2, 0.25, 230, 0.36)]
    stats = []
    irs = [chip_fragment_ir(rng) for _ in range(24)]
    for (t0, dur, nf, gain) in phases:
        # a chip is a stack of brittle cell layers / ridges: each one is its own small fibre
        # bundle (precursor micro-cracks + a final avalanche) failing at its own strain, so a
        # bite is a train of fractures spread over the jaw closure instead of one big snap.
        n_layers = max(3, nf // 45)
        n_ev = 0
        for L in range(n_layers):
            ev = fiber_bundle_1d(n=int(rng.integers(30, 90)), steps=300, weibull_k=rng.uniform(1.3, 2.5),
                                 seed=rng.integers(1e9))
            if not ev:
                continue
            s_max = max(e[0] for e in ev)
            onset = rng.beta(1.6, 1.4)  # where in the closure this layer lets go
            span = rng.uniform(0.04, 0.25)
            for (s, size, energy) in ev:
                frac = onset + span * (s / max(s_max, 1) - 1)
                if frac < 0:
                    continue
                tt = t0 + dur * frac ** 0.7 + rng.normal(0, 0.0003)
                amp = gain * np.sqrt(energy) / 6.0 * rng.uniform(0.6, 1.2)
                burst = np.zeros(int(0.003 * SR))
                for j in range(min(size, 10)):
                    cb = crack_burst(rng, dur_ms=rng.uniform(0.04, 0.15), hp=rng.uniform(700, 2000), lp=12000)
                    place(burst, j * rng.uniform(5e-5, 4e-4), cb * rng.uniform(0.5, 1))
                y = fftconv(burst, irs[rng.integers(len(irs))])
                y[:len(burst)] += 0.5 * burst  # direct crack radiation + fragment ringing
                place(out, tt, y * amp)
                n_ev += 1
        stats.append(n_ev)
    # mouth/teeth cavity colouring + very close mic: a broad 1.6 kHz bump, slight 8 kHz air
    out = filt(out, ("peak", 1600, 1.0, 2), ("highshelf", 7000, 0.7, 2), ("hp", 120))
    # quiet saliva / tongue texture between chews (tiny clicks, very low level)
    tex = np.zeros_like(out)
    for tt in np.cumsum(rng.exponential(0.06, 200)):
        if tt > seconds - 0.1:
            break
        place(tex, tt, crack_burst(rng, 0.05, 3000) * rng.uniform(0, 0.01))
    out += tex
    return fade(out), {'avalanches_per_phase': stats}


# =========================================================== 4. fire crackle

def hawkes(rate, seconds, branch=0.6, tau=0.04, rng=None):
    """Self-exciting point process (cluster representation)."""
    rng = rng_of(rng)
    parents = np.cumsum(rng.exponential(1 / rate, int(rate * seconds * 3) + 10))
    parents = parents[parents < seconds]
    ev = list(parents)
    gen = list(parents)
    while gen:
        nxt = []
        for t in gen:
            for _ in range(rng.poisson(branch)):
                c = t + rng.exponential(tau)
                if c < seconds:
                    nxt.append(c)
        ev += nxt
        gen = nxt
    return np.sort(np.array(ev))


def fire_crackle(seconds=10.0, seed=4):
    rng = rng_of(seed)
    n = int(seconds * SR)
    out = np.zeros(n)
    times = hawkes(4.0, seconds, branch=0.65, tau=0.035, rng=rng)
    amps = np.minimum(rng.pareto(1.6, len(times)) + 0.05, 8) / 8
    for t, a in zip(times, amps):
        # steam/resin pocket burst: very short broadband pop, random colour
        fc = rng.uniform(900, 7000)
        pop = crack_burst(rng, dur_ms=rng.uniform(0.04, 0.35), hp=rng.uniform(300, 1500))
        pop = filt(pop, ('peak', fc, rng.uniform(0.8, 2.5), rng.uniform(3, 9)), tail=0.01)
        if rng.random() < 0.3:  # an ember fragment flies off and rings briefly
            fr = rng.uniform(2500, 9000) * np.array([1, 1.6, 2.3])
            pop = np.r_[pop, np.zeros(int(0.03 * SR))]
            pop[:int(0.03 * SR)] += 0.3 * damped_sines(fr, fr * 0.06, [1, 0.5, 0.3], 0.03,
                                                       phases=rng.uniform(0, TAU, 3))
        place(out, t, pop * a)
    # hiss: escaping gas, >2.5 kHz, slowly fluctuating
    mod = onepole_lp(rng.standard_normal(n), 1.5)
    mod = np.clip(0.5 + 2.5 * mod / (np.std(mod) + 1e-9) * 0.3, 0, None)
    hiss = filt(white(n, rng), ('hp', 2500, 0.7), ('lp', 12000)) * mod * 0.012
    # roar / lapping: brown noise under 250 Hz with gusty modulation (combustion turbulence)
    g = onepole_lp(rng.standard_normal(n), 3.0)
    g = 0.6 + 0.4 * np.tanh(g / (np.std(g) + 1e-9))
    roar = filt(colored(n, -6, rng), ('lp', 260, 0.7), ('hp', 35)) * g * 0.06
    # occasional log settling: soft low thump + debris
    for t in rng.uniform(1, seconds - 1, 2):
        th = damped_sines([95, 160], [35, 60], [1, 0.5], 0.4) * 0.15
        place(out, t, th)
    out = out + hiss + roar
    return fade(out, 0.2, 0.3), {'pops': int(len(times)), 'pops_per_s': round(len(times) / seconds, 1)}


# =========================================================== 5. slime squish

def cavity_pop(rng, f0, q, dur):
    """Air pocket breaking open: Helmholtz resonance whose neck widens -> rising pitch,
    plus a film-rupture tick at the start."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 * (1 + 2.5 * (1 - np.exp(-t / (dur * 0.35))))  # aperture grows
    ph = TAU * np.cumsum(f) / SR
    d = np.pi * f0 / q
    y = np.sin(ph) * np.exp(-d * t) * (1 - np.exp(-t / 0.0002))
    tick = crack_burst(rng, 0.04, 2500) * 0.6
    y[:len(tick)] += tick[:n]
    return y


def granular_formant_noise(env, fc_curve, q=2.0, grain=0.02, rng=None):
    """Time-varying band-pass noise via overlap-added Hann grains, each with a fixed biquad."""
    rng = rng_of(rng)
    n = len(env)
    g = int(grain * SR); hop = g // 2
    win = np.hanning(g)
    out = np.zeros(n + g)
    for i in range(0, n - g, hop):
        e = env[i + hop // 2]
        if e < 1e-4:
            continue
        x = rng.standard_normal(g)
        x = filt(x, ('bp', fc_curve[i + hop // 2], q), tail=0.0) * win * e
        out[i:i + g] += x
    return out[:n]


def slime_squish(seconds=8.0, seed=5):
    rng = rng_of(seed)
    n = int(seconds * SR)
    out = np.zeros(n)
    t = np.arange(n) / SR
    # squeeze cycles (hand closes, then opens)
    P = np.zeros(n)
    starts = np.arange(0.3, seconds - 1.0, 1.15) + rng.normal(0, 0.05, 100)[:len(np.arange(0.3, seconds - 1.0, 1.15))]
    for s in starts:
        close, open_ = rng.uniform(0.35, 0.5), rng.uniform(0.3, 0.45)
        tt = t - s
        up = (tt >= 0) & (tt < close)
        dn = (tt >= close) & (tt < close + open_)
        P[up] = np.maximum(P[up], np.sin(np.pi / 2 * tt[up] / close) ** 2)
        P[dn] = np.maximum(P[dn], np.cos(np.pi / 2 * (tt[dn] - close) / open_) ** 2)
    dP = np.gradient(P) * SR
    # pops: inhomogeneous Poisson; pockets burst while compressing (dP>0) and fresh pockets
    # snap open while releasing (dP<0, fewer but larger)
    rate = 55 * np.clip(dP, 0, None) / 2.5 + 22 * np.clip(-dP, 0, None) / 2.5 + 1.0 * P
    lam_max = rate.max()
    cand = np.cumsum(rng.exponential(1 / lam_max, int(lam_max * seconds * 1.5)))
    cand = cand[cand < seconds - 0.05]
    keep = cand[rng.random(len(cand)) < rate[(cand * SR).astype(int)] / lam_max]
    for tp in keep:
        r = np.exp(rng.uniform(np.log(0.6e-3), np.log(5e-3)))  # pocket radius
        f0 = np.clip(1.6 / r, 300, 3500)  # bigger pockets lower (viscous medium, not water)
        y = cavity_pop(rng, f0, q=rng.uniform(2.5, 6), dur=rng.uniform(0.004, 0.012))
        a = (r / 5e-3) ** 0.5 * rng.uniform(0.4, 1.0)
        place(out, tp, y * a)
    # stringy adhesion release while opening: a fizz of tiny high clicks
    for tp in keep[rng.random(len(keep)) < 0.3]:
        for k in range(rng.integers(3, 12)):
            place(out, tp + rng.uniform(0, 0.05), crack_burst(rng, 0.02, 4000) * rng.uniform(0.02, 0.08))
    # squelch: viscous flow noise, formant follows pressure (150 -> 900 Hz)
    env = 0.25 * np.abs(dP) / (np.abs(dP).max() + 1e-9) + 0.04 * P
    fc = 180 + 700 * P
    squelch = granular_formant_noise(env, fc, q=1.6, rng=rng)
    out = out + 0.5 * squelch
    out = filt(out, ('hp', 60), ('peak', 2200, 1.2, 2))
    return fade(out, 0.05, 0.2), {'pops': int(len(keep)), 'pops_per_s': round(len(keep) / seconds, 1)}


# =========================================================== 6. water drops / bubbles

def bubble(r, seconds=None, xi=0.1, eps=1.0, rng=None):
    """van den Doel (2005) bubble: p(t)= a sin(2 pi f0 (t + sigma t^2/2)) e^{-d t};
    f0 = 3/r [Hz, r in m], d = 0.13/r + 0.0072 r^-1.5, sigma = xi * d."""
    f0 = 3.0 / r
    d = 0.13 / r + 0.0072 * r ** -1.5
    sigma = xi * d
    seconds = seconds or min(0.25, 8.0 / d)
    t = np.arange(int(seconds * SR)) / SR
    a = eps * r ** 1.0
    ph = TAU * f0 * (t + 0.5 * sigma * t * t)
    y = a * np.sin(ph) * np.exp(-d * t)
    y[:int(0.0002 * SR)] *= np.linspace(0, 1, int(0.0002 * SR))
    return y, f0, d


def water_drops(seconds=10.0, seed=6):
    """Drips falling into a ceramic bowl of water; occasional double drops."""
    rng = rng_of(seed)
    n = int(seconds * SR)
    out = np.zeros(n)
    t = 0.3
    log = []
    bowl_f = np.array([610, 1480, 2690, 4100]) * rng.uniform(0.97, 1.03)
    while t < seconds - 0.4:
        # impact splash: soft, short, mostly < 5 kHz
        sp = filt(rng.standard_normal(int(0.004 * SR)) * np.exp(-np.arange(int(0.004 * SR)) / (0.0008 * SR)),
                  ('lp', rng.uniform(3000, 6000)), ('hp', 400), tail=0.01)
        place(out, t, sp * rng.uniform(0.08, 0.2))
        # the very first contact of drop and surface: a sharp, weak pressure pulse (Franz 1959)
        place(out, t, crack_burst(rng, 0.08, 500, 9000) * rng.uniform(0.08, 0.2))
        if rng.random() < 0.35:  # big drop: low 'plop' of the collapsing crater (r 4-8 mm bubble)
            yp, _, _ = bubble(rng.uniform(4e-3, 8e-3), xi=0.05)
            place(out, t + rng.uniform(0.01, 0.025), yp / 8e-3 * rng.uniform(0.4, 0.8))
        for k in range(rng.poisson(1.5)):  # splash droplets falling back 40-120 ms later
            yd, _, _ = bubble(rng.uniform(0.25e-3, 0.6e-3), xi=0.1)
            place(out, t + rng.uniform(0.04, 0.12), yd / 2.6e-3 * rng.uniform(0.3, 0.9)
                  + 0 * yd)
        # bowl ring excited by the pressure pulse through the water
        bw = damped_sines(bowl_f, _loss_decay(bowl_f, 0.012), [0.2, 0.1, 0.05, 0.03], 0.4,
                          phases=rng.uniform(0, TAU, 4))  # water-loaded bowl on a table: damped
        place(out, t, bw * 0.004)
        if rng.random() < 0.8:  # regular entrainment -> the 'plink'
            r = np.exp(rng.uniform(np.log(0.9e-3), np.log(2.6e-3)))
            delay = rng.uniform(0.004, 0.012)  # cavity collapse happens a few ms after impact
            y, f0, d = bubble(r, xi=rng.uniform(0.07, 0.16), eps=1.0)
            place(out, t + delay, y / 2.6e-3 * rng.uniform(0.6, 1.0))
            log.append((round(f0), round(d)))
            if rng.random() < 0.25:  # a second, smaller bubble pinches off
                y2, f2, d2 = bubble(r * rng.uniform(0.4, 0.7), xi=0.1)
                place(out, t + delay + rng.uniform(0.003, 0.02), y2 / 2.6e-3 * 0.5)
        t += rng.uniform(0.25, 0.8)
    # the room: a close, small reflective kitchen (two early reflections + short tail)
    er = np.zeros(int(0.03 * SR)); er[0] = 1; er[int(0.0031 * SR)] = 0.3; er[int(0.0074 * SR)] = 0.18
    out = fftconv(out, er)[:n]
    return fade(out), {'bubbles': len(log), 'f0_range': [min(l[0] for l in log), max(l[0] for l in log)],
                       'damping_range': [min(l[1] for l in log), max(l[1] for l in log)]}


def bubbling(seconds=6.0, seed=7, rate=60.0):
    """Blowing through a straw into water: Poisson bubbles, radius power law p(r)~r^-2.5."""
    rng = rng_of(seed)
    n = int(seconds * SR)
    out = np.zeros(n)
    env = np.clip(np.sin(np.pi * np.arange(n) / n * 1.0) * 1.4, 0, 1)
    times = np.cumsum(rng.exponential(1 / rate, int(rate * seconds * 2)))
    times = times[times < seconds - 0.1]
    rmin, rmax, beta = 0.6e-3, 6e-3, 2.5
    u = rng.random(len(times))
    r = (rmin ** (1 - beta) + u * (rmax ** (1 - beta) - rmin ** (1 - beta))) ** (1 / (1 - beta))
    for tt, rr in zip(times, r):
        if rng.random() > env[int(tt * SR)]:
            continue
        y, f0, d = bubble(rr, xi=rng.uniform(0.05, 0.2))
        place(out, tt, y / rmax * rng.uniform(0.5, 1))
    gurgle = filt(colored(n, -6, rng), ('lp', 300)) * env * 0.01
    # bubbles bursting at the surface throw tiny droplets: short noise splashes
    splash = np.zeros(n)
    for tt in times[rng.random(len(times)) < 0.5]:
        m = int(rng.uniform(0.002, 0.008) * SR)
        bb = rng.standard_normal(m) * np.exp(-np.arange(m) / (m / 4))
        place(splash, tt + rng.uniform(0.005, 0.03), bb * rng.uniform(0.05, 0.2))
    splash = filt(splash, ('hp', 1500), ('lp', 12000))
    return fade(out + gurgle + splash), {'bubbles': int(len(times))}


# =========================================================== 7a. glass shatter

def glass_shatter(seconds=4.0, seed=8):
    """A drinking glass hits a tiled floor and shatters."""
    rng = rng_of(seed)
    n = int(seconds * SR)
    out = np.zeros(n)
    t0 = 0.25
    g = 9.81
    # (1) impact on floor: glass body modes struck hard, then cut short by the fracture
    fm = glass_modes(1150.0, 6)
    body = damped_sines(fm, _loss_decay(fm, 0.0008), 1 / np.arange(2, 8), 0.6, phases=rng.uniform(0, TAU, 6))
    body *= np.exp(-np.arange(len(body)) / SR / 0.012)  # fracture kills the ringing in ~12 ms
    place(out, t0, body * 0.25)
    # floor 'tock' (tile on screed): low-mid, heavily damped
    place(out, t0, damped_sines([180, 420, 950], [90, 160, 300], [0.5, 0.35, 0.2], 0.3) * 0.3)
    # (2) fracture: a few ms of very bright crack noise (many simultaneous crack fronts)
    fr = np.zeros(int(0.12 * SR))
    for k in range(160):  # crack fronts branch for ~30-60 ms after the hit
        place(fr, min(rng.exponential(0.012), 0.11), crack_burst(rng, rng.uniform(0.02, 0.12), 1500, 18000)
              * rng.uniform(0.2, 1))
    place(out, t0, fr * 0.6)
    # (3) fragments: power-law sizes N(>a) ~ a^-1.7, 6 mm - 60 mm
    nfrag = 260
    amin, amax, D = 0.006, 0.06, 1.7
    u = rng.random(nfrag)
    a = (amin ** -D - u * (amin ** -D - amax ** -D)) ** (-1 / D)
    n_events = 0
    for ai in a:
        # free square glass plate (h = 2.5 mm): f1 ~ 10.1/a^2 * (h/3mm)
        f1 = 10.08 / ai ** 2 * (2.5 / 3)
        fr_modes = f1 * np.array([1.0, 1.47, 1.86, 2.55, 3.2]) * rng.uniform(0.94, 1.06, 5)
        mass = 2500 * 0.0025 * ai ** 2
        v_up = rng.uniform(0.2, 1.8)
        h0 = rng.uniform(0.0, 0.08)
        tt = t0 + 0.002 + (v_up + np.sqrt(v_up ** 2 + 2 * g * h0)) / g  # first landing
        v = np.sqrt(v_up ** 2 + 2 * g * h0)
        e = rng.uniform(0.25, 0.45)
        while v > 0.06 and tt < seconds - 0.05:
            amp = v * np.sqrt(mass / 0.002) * rng.uniform(0.6, 1.2)
            # contact click (small shards' modes are ultrasonic -> their impact is a click)
            click = crack_burst(rng, rng.uniform(0.02, 0.06), 1500, 18000)
            ring = damped_sines(fr_modes, _loss_decay(fr_modes, rng.uniform(0.002, 0.006)),
                                rng.uniform(0.2, 1, 5), 0.25, phases=rng.uniform(0, TAU, 5))
            y = np.r_[click, np.zeros(len(ring) - len(click))] * 1.0 + ring * 0.5
            place(out, tt, y * amp * 0.05)
            n_events += 1
            v *= e
            tt += 2 * v / g + rng.uniform(0, 0.004)
        # after bouncing, some shards skid: a short burst of micro-impacts
        if rng.random() < 0.35 and tt < seconds - 0.3:
            for k in range(rng.integers(3, 9)):
                place(out, tt + k * rng.uniform(0.006, 0.02),
                      crack_burst(rng, 0.03, 3000) * 0.01 * np.sqrt(mass / 0.002))
    out = filt(out, ('hp', 50))
    return fade(out, 0.0, 0.2), {'fragments': nfrag, 'impact_events': n_events}


# =========================================================== 7b. kinetic sand cutting

def sand_cut(seconds=6.0, seed=9):
    """A knife slicing a block of kinetic sand twice; the slice slumps over after each cut."""
    rng = rng_of(seed)
    n = int(seconds * SR)
    out = np.zeros(n)
    t = np.arange(n) / SR
    cuts = [(0.4, 1.3), (3.0, 1.1)]
    for (s, dur) in cuts:
        # knife speed profile: accelerate, steady, decelerate (a smooth bump)
        tt = (t - s) / dur
        on = (tt >= 0) & (tt <= 1)
        speed = np.zeros(n)
        speed[on] = np.sin(np.pi * tt[on]) ** 0.8
        # grain stick-slip events: rate ~ speed * 4000/s, lognormal sizes
        lam = 4000 * speed
        lam_max = lam.max()
        cand = np.cumsum(rng.exponential(1 / lam_max, int(lam_max * dur * 1.3)))
        cand = s + cand[cand < dur]
        keep = cand[rng.random(len(cand)) < lam[(cand * SR).astype(int)] / lam_max]
        imp = np.zeros(n)
        idx = (keep * SR).astype(int)
        np.add.at(imp, idx, rng.lognormal(0, 0.9, len(idx)) * np.sign(rng.standard_normal(len(idx))))
        # grain contact resonance: tiny grains -> high, broad; cohesive coating damps it
        gr = filt(imp, ('bp', 3800, 0.9), ('peak', 7500, 1.5, 3), ('hp', 600))
        out += gr * 0.05
        # occasional bigger crumb snaps when the blade breaks cohesive clusters
        for tc in keep[rng.random(len(keep)) < 0.004]:
            place(out, tc, crack_burst(rng, rng.uniform(0.05, 0.15), 900, 9000) * rng.uniform(0.1, 0.3))
        # blade friction against the steel: faint high hiss following the speed
        out += filt(white(n, rng), ('bp', 6000, 0.7)) * speed * 0.004
        # (2) slab slump: a soft, heavily damped low thud + granular scatter
        ts = s + dur + rng.uniform(0.15, 0.3)
        thud = damped_sines([75, 140, 260], [45, 80, 140], [1, 0.6, 0.3], 0.4, phases=[0, 0.5, 1])
        thud *= 1 - np.exp(-np.arange(len(thud)) / SR / 0.006)  # soft onset (cohesive mass)
        place(out, ts, thud * 0.35)
        sc = np.zeros(int(0.25 * SR))
        for k in range(300):
            place(sc, rng.exponential(0.05), crack_burst(rng, 0.03, 2500) * rng.uniform(0, 0.03))
        place(out, ts, filt(sc, ('lp', 9000)))
    return fade(out), {'cuts': len(cuts)}


# =========================================================== recording chain (for fair comparison)

def record(x, room='small', dist=0.25, noise_dbfs=-72.0, seed=0):
    """Pretend a microphone recorded this in a room: direct + first-order image sources of a
    4 x 3.5 x 2.6 m room (absorption 0.3) + exponential diffuse tail (RT60 0.35 s) + pink noise floor.
    Source and mic sit 0.8 m above a table/floor; dist = source-mic distance."""
    rng = rng_of(seed)
    c = 343.0
    L = np.array([4.0, 3.5, 2.6])
    src = np.array([1.7, 1.6, 0.9]); mic = src + np.array([dist, 0.0, 0.05])
    ir = np.zeros(int(0.5 * SR))
    def add(p, refl):
        d = np.linalg.norm(p - mic)
        i = d / c * SR
        g = refl / max(d, 0.05)
        k = int(i); fr = i - k
        if k + 1 < len(ir):
            ir[k] += g * (1 - fr); ir[k + 1] += g * fr
    add(src, 1.0)
    beta = np.sqrt(1 - 0.3)
    for ax in range(3):
        for wall in (0.0, L[ax]):
            p = src.copy(); p[ax] = 2 * wall - src[ax]
            add(p, beta * (1.4 if (ax == 2 and wall == 0.0) else 1.0) * 0.8)  # table/floor is hard
    t = np.arange(len(ir)) / SR
    t0 = 0.012
    tail = rng.standard_normal(len(ir)) * np.exp(-6.91 * t / 0.35) * (t > t0)
    tail = filt(tail, ('lp', 7000), ('hp', 120))
    direct_e = (1 / dist) ** 2
    tail *= np.sqrt(direct_e * 0.06 / (np.sum(tail ** 2) + 1e-12))  # D/R ~ +12 dB at 25 cm
    ir += tail
    ir /= ir.max()
    y = fftconv(x, ir)[:len(x)]
    y = y / (np.max(np.abs(y)) + 1e-12) * 0.5
    nf = colored(len(y), -3, rng) * 0.5 * 10 ** (noise_dbfs / 20)
    return y + nf
