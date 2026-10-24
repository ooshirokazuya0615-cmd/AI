"""A/V sync check on the final MP4 (decoded back, not the intermediate WAV)."""
import json, subprocess, sys
import numpy as np
sys.dont_write_bytecode = True
import sim, stickman_scene as S

mp4 = sys.argv[1] if len(sys.argv) > 1 else 'preview.mp4'
probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', mp4],
                                  capture_output=True, text=True).stdout)
for st in probe['streams']:
    print(st['codec_type'], st['codec_name'], 'start', st.get('start_time'), 'dur', st.get('duration'),
          st.get('r_frame_rate', ''), st.get('width', ''), st.get('height', ''), st.get('sample_rate', ''))

rec = sim.simulate(sim.Params(**S.TAKE))
tl = S.Timeline(rec)
big = [(t, s) for (t, x, y, s) in tl.big]

# ---- audio: onset envelope from the decoded AAC ----
SR = 48000
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', mp4, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                     capture_output=True).stdout
x = np.frombuffer(raw, '<f4')
hop = 48                                   # 1 ms frames, time-domain (no STFT window delay)
size = 1 << int(np.ceil(np.log2(len(x))))
fq = np.fft.rfftfreq(size, 1 / SR)
y = np.fft.irfft(np.fft.rfft(x, size) / (1 + (900 / np.maximum(fq, 1)) ** 4), size)[:len(x)]   # >900 Hz
e = (y[:len(y) // hop * hop].reshape(-1, hop) ** 2).sum(axis=1)
le = 10 * np.log10(e + 1e-10)
flux = np.maximum(np.diff(le, prepend=le[0]), 0)
imp = np.zeros_like(flux)
for t, s in big:
    k = int(round(t * SR / hop))
    if k < len(imp):
        imp[k] += s
lags = np.arange(-100, 101)                 # ms
cc = [np.dot(np.roll(imp, L), flux) for L in lags]
best = lags[int(np.argmax(cc))]
print(f'audio: cross-correlation lag (audio vs contact events) = {best:+d} ms')
errs = []
for t, s in big:
    k = int(round(t * SR / hop))
    w = flux[max(k - 30, 0):k + 31]
    if len(w) == 61:
        errs.append(int(np.argmax(w)) - 30)
errs = np.array(errs)
print(f'audio: per-hit onset error over {len(errs)} big hits: median {np.median(errs):+.1f} ms, '
      f'|err|<=5ms for {np.mean(np.abs(errs) <= 5) * 100:.0f}%')

# ---- video: comic-burst (accent colour) onsets from decoded frames ----
w, h = 270, 480
fps = 60
rawv = subprocess.run(['ffmpeg', '-v', 'error', '-i', mp4, '-vf', f'scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                      capture_output=True).stdout
v = np.frombuffer(rawv, np.uint8).reshape(-1, h, w, 3).astype(np.int16)
acc = np.array([255, 179, 31])
cnt = (np.abs(v - acc).sum(axis=3) < 60).sum(axis=(1, 2)).astype(float)
rise = np.maximum(np.diff(cnt, prepend=0), 0)
vimp = np.zeros(len(cnt))
for t, s in big:
    f = int(round(t * fps))
    if f < len(vimp):
        vimp[f] += s
vl = np.arange(-6, 7)
vcc = [np.dot(np.roll(vimp, L), rise) for L in vl]
vbest = vl[int(np.argmax(vcc))]
print(f'video: burst onset lag vs contact events = {vbest:+d} frames ({vbest * 1000 / fps:+.1f} ms), frames={len(cnt)}')
print(f'=> picture-to-sound offset = {best - vbest * 1000 / fps:+.1f} ms  (|x| < 1 frame = {1000 / fps:.1f} ms is perfect)')
