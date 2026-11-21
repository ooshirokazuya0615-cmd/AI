#!/usr/bin/env python3
"""Driver: sim -> GLSL frames (moderngl, repo Gpu class) -> numpy audio -> ffmpeg MP4."""
import argparse, json, os, subprocess, sys, time
from pathlib import Path
sys.dont_write_bytecode = True           # never write .pyc into the repo
sys.path.insert(0, '/home/user/AI/tools/nonverbal')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np
import render                            # repo: Gpu, master_audio, Config, video_filters
import sim, stickman_scene

ap = argparse.ArgumentParser()
ap.add_argument('--size', default='1080x1920')
ap.add_argument('--fps', type=int, default=60)
ap.add_argument('--still', help='comma separated seconds -> PNGs instead of video')
ap.add_argument('-o', '--out', default=str(HERE / 'preview.mp4'))
ap.add_argument('--crf', type=int, default=18)
ap.add_argument('--preset', default='medium')
a = ap.parse_args()
w, h = (int(v) for v in a.size.split('x'))
cfg = render.Config(width=w, height=h, fps=a.fps, seconds=9, seed=3)
meas = {}

t0 = time.time()
rec = sim.simulate(sim.Params(**stickman_scene.TAKE))
meas['sim_seconds_wall'] = round(time.time() - t0, 3)
meas['sim_steps'] = rec.steps
meas['sim_seconds_simulated'] = round(rec.steps * sim.DT, 3)
meas['events'] = len(rec.events)
meas['story'] = {k: (v if not hasattr(v, 'item') else v.item()) for k, v in sim.evaluate(rec)[2].items()}

gpu = render.Gpu(w, h)
meas['renderer'] = gpu.renderer
scene = stickman_scene.Scene(gpu, cfg, rec)
print('renderer', gpu.renderer, 'frames', scene.frame_count, 't_hit', rec.t_hit, 't_pad', scene.tl.t_pad, 't_settle', scene.tl.t_settle)

def frame_rgb(f):
    scene.render(f)
    return gpu.read()

if a.still:
    out = Path(a.out).with_suffix('')
    for s in a.still.split(','):
        f = min(int(round(float(s) * cfg.fps)), scene.frame_count - 1)
        png = f'{out}-{float(s):05.2f}s.png'
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                        '-s', f'{w}x{h}', '-i', '-', '-vf', 'vflip', '-frames:v', '1', png], input=frame_rgb(f), check=True)
        print(png)
    sys.exit()

# ---- audio ----
t0 = time.time()
buf = scene.audio()
meas['audio_synth_seconds'] = round(time.time() - t0, 3)
wav = HERE / 'audio.wav'
t0 = time.time()
render.master_audio(buf, wav)
meas['audio_master_seconds'] = round(time.time() - t0, 3)
meas['sound_events_used'] = len(scene.sound_events)
meas['sound_tally'] = scene.sound_tally
json.dump([{k: (round(v, 5) if isinstance(v, float) else v) for k, v in e.items()} for e in rec.events],
          open(HERE / 'contact_events.json', 'w'), indent=0)

# ---- render-only benchmark on a slice (no ffmpeg) ----
t0 = time.time()
nb = min(60, scene.frame_count)
for f in range(0, scene.frame_count, max(1, scene.frame_count // nb)):
    scene.render(f); gpu.read()
meas['render_only_fps'] = round(nb / (time.time() - t0), 2)

# ---- full encode ----
cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
       '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(cfg.fps), '-i', '-',
       '-i', str(wav), '-vf', render.video_filters(),
       '-c:v', 'libx264', '-preset', a.preset, '-crf', str(a.crf), '-profile:v', 'high',
       '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
       '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', a.out]
ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
t_draw = t_read = t_pipe = 0.0
t0 = time.time()
for f in range(scene.frame_count):
    ta = time.time(); scene.render(f); tb = time.time(); data = gpu.read(); tc = time.time()
    ff.stdin.write(data); td = time.time()
    t_draw += tb - ta; t_read += tc - tb; t_pipe += td - tc
    if f % 60 == 0:
        print(f'\r  frame {f}/{scene.frame_count}', end='', flush=True)
ff.stdin.close(); ff.wait()
total = time.time() - t0
print()
meas['frames'] = scene.frame_count
meas['pipeline_seconds'] = round(total, 2)
meas['pipeline_fps'] = round(scene.frame_count / total, 2)
meas['breakdown_seconds'] = dict(draw_submit=round(t_draw, 2), readback=round(t_read, 2), pipe_to_ffmpeg=round(t_pipe, 2))
json.dump(meas, open(HERE / f'measurements-{w}x{h}.json', 'w'), indent=1)
print(json.dumps(meas, indent=1))
