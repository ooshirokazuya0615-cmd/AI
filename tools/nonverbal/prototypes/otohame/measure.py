#!/usr/bin/env python3
"""
Measure A/V sync of the ENCODED mp4 (not the internal schedule).

audio : decode AAC from the mp4 -> onset of each scheduled landing (HF energy rise)
        + global lag by cross-correlating against the pre-encode master wav
video : decode frames -> per-frame features
        - cut frames (mean abs frame difference spike)          -> landings on downbeats
        - blob colour mask: bottom-edge velocity discontinuity  -> contact frame
        - mean-luminance jump (pillar flash)                    -> flash frame
offset = video_event_time - audio_onset_time  (+ = picture late)
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score as S  # noqa: E402

SR = 48000


def ffprobe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def frame_times(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                          'frame=best_effort_timestamp_time', '-of', 'csv=p=0', str(path)],
                         capture_output=True, text=True, check=True).stdout
    return np.array([float(x.strip(',')) for x in out.split() if x.strip(',').strip()])


def decode_audio(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0', '-ac', '1', '-ar', str(SR),
                          '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, '<f4').astype(float)


def read_wav_mono(path):
    import wave
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, 2).mean(1) / 32768
    return x


def onset_near(x, t, pre=0.030, post=0.050):
    """first sample where the high-passed energy envelope crosses 30% of its local rise."""
    d = np.diff(x, prepend=x[0])                        # crude high-pass (emphasises transients)
    env = np.convolve(np.abs(d), np.ones(48) / 48, mode='same')   # 1 ms
    i0, i1 = int((t - pre) * SR), int((t + post) * SR)
    seg = env[i0:i1]
    base = np.median(env[int((t - pre) * SR):int((t - 0.004) * SR)])
    peak = seg.max()
    thr = base + 0.3 * (peak - base)
    k = int(np.argmax(seg > thr))
    return (i0 + k) / SR


def decode_video_features(path, w, h):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:v:0', '-f', 'rawvideo',
                          '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    n = w * h * 3
    feats, prev = [], None
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        im = np.frombuffer(buf, np.uint8).reshape(h, w, 3).astype(np.float32) / 255
        r, g, b = im[..., 0], im[..., 1], im[..., 2]
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        mx, mn = im.max(-1), im.min(-1)
        sat = (mx - mn) / (mx + 1e-6)
        hue = np.where((mx == r) & (mx > mn), ((g - b) / (mx - mn + 1e-6)) / 6 % 1, -1)
        mask = (hue > 0.04) & (hue < 0.16) & (sat > 0.40) & (mx > 0.35)   # orange/yellow blob (hue fitted on decoded frames)
        ys, xs = np.nonzero(mask)
        if len(ys) > 30:
            bot, top = np.percentile(ys, 99), np.percentile(ys, 1)
            left, right = np.percentile(xs, 1), np.percentile(xs, 99)
            box = (top, bot, left, right, len(ys))
        else:
            box = (np.nan,) * 4 + (0,)
        small = lum[::4, ::4]
        diff = float(np.abs(small - prev).mean()) if prev is not None else 0.0
        prev = small
        feats.append((float(lum.mean()), diff, *box))
    p.wait()
    return np.array(feats)


def main(mp4=HERE / 'otohame.mp4', wav=HERE / 'audio.wav'):
    info = ffprobe(mp4)
    vs = next(s for s in info['streams'] if s['codec_type'] == 'video')
    as_ = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    w, h = int(vs['width']), int(vs['height'])
    fps = eval(vs['r_frame_rate'])
    ft = frame_times(mp4)
    print(f"video start {vs.get('start_time')}  audio start {as_.get('start_time')}  "
          f"frames {len(ft)}  fps {fps:.3f}  first pts {ft[0]:.4f}")

    a = decode_audio(mp4)
    ref = read_wav_mono(wav)
    m = min(len(a), len(ref), 4 * SR)
    X = np.fft.rfft(a[:m], 2 * m)
    Y = np.fft.rfft(ref[:m], 2 * m)
    cc = np.fft.irfft(X * np.conj(Y))
    lag = int(np.argmax(np.abs(cc)))
    lag = lag if lag < m else lag - 2 * m
    print(f'AAC decode vs master wav: lag {lag} samples = {lag / SR * 1000:+.3f} ms')

    feats = decode_video_features(mp4, w, h)
    lum, diff = feats[:, 0], feats[:, 1]
    top, bot, left, right, area = feats[:, 2], feats[:, 3], feats[:, 4], feats[:, 5], feats[:, 6]
    thr = np.median(diff) * 6 + 0.01
    cut_frames = [k for k in range(1, len(diff)) if diff[k] > thr and diff[k] > 2.5 * max(diff[k - 1], diff[min(k + 1, len(diff) - 1)])]

    notes = S.lead_notes()
    downs = set(round(t, 4) for t in S.downbeats())
    rows = []
    for nt in notes:
        ta = onset_near(a, nt.t)
        k_exp = int(round(nt.t * fps))
        if round(nt.t, 4) in downs:
            ks = [k for k in cut_frames if abs(k - k_exp) <= 6]
            k = ks[0] if ks else None
            method = 'cut'
        else:
            # contact = biggest drop in downward screen velocity of the blob's bottom edge
            v = np.diff(bot)                      # px per frame, + = moving down the screen
            lo, hi = k_exp - 5, k_exp + 5
            cand = [(v[j - 1] - v[j], j) for j in range(lo, hi) if np.isfinite(v[j - 1]) and np.isfinite(v[j])]
            k = max(cand)[1] if cand else None   # frame j: last frame of the fall = contact frame
            method = 'contact'
        dl = np.diff(lum, prepend=lum[0])
        kf = int(np.argmax(dl[k_exp - 4:k_exp + 5])) + k_exp - 4
        tv = ft[k] if k is not None else np.nan
        rows.append(dict(note=nt.idx, midi=nt.midi, sched=round(nt.t, 4), audio_onset=round(ta, 4),
                         audio_err_ms=round((ta - nt.t) * 1000, 2), method=method, frame=k,
                         video_t=round(float(tv), 4), av_ms=round((tv - ta) * 1000, 2),
                         flash_frame=kf, flash_av_ms=round((ft[kf] - ta) * 1000, 2)))
    for r in rows:
        print(r)
    av = np.array([r['av_ms'] for r in rows])
    fl = np.array([r['flash_av_ms'] for r in rows])
    ae = np.array([r['audio_err_ms'] for r in rows])
    summ = dict(n=len(rows), av_mean=float(np.nanmean(av)), av_absmax=float(np.nanmax(np.abs(av))),
                flash_av_mean=float(fl.mean()), flash_av_absmax=float(np.abs(fl).max()),
                audio_onset_err_mean=float(ae.mean()), audio_onset_err_absmax=float(np.abs(ae).max()),
                cut_frames=[int(k) for k in cut_frames], cut_times=[round(float(ft[k]), 4) for k in cut_frames],
                aac_lag_ms=lag / SR * 1000, frame_period_ms=1000 / fps)
    print(json.dumps(summ, indent=1))
    (HERE / 'sync_report.json').write_text(json.dumps(dict(rows=rows, summary=summ), indent=1))
    np.save(HERE / 'video_feats.npy', feats)


if __name__ == '__main__':
    main(*sys.argv[1:])
