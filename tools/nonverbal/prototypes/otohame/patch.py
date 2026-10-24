#!/usr/bin/env python3
"""Stateless segment re-render: re-render frames [a, b] and splice them into an existing mp4."""
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402

src, a, b, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
w, h, fps = 1080, 1920, 60
gpu = build.R.Gpu(w, h)
rd = build.Renderer(gpu, w, h, fps)
dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', src, '-map', '0:v:0', '-vf',
                        'scale=in_color_matrix=bt709:in_range=tv', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                       stdout=subprocess.PIPE)
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}',
                        '-r', str(fps), '-i', '-', '-i', str(HERE / 'audio.wav'),
                        '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
                        '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-profile:v', 'high',
                        '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                        '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', out],
                       stdin=subprocess.PIPE)
n = w * h * 3
t0 = time.time()
for f in range(rd.frame_count):
    old = dec.stdout.read(n)
    if a <= f <= b:
        rd.render(f)
        frame = np.flipud(np.frombuffer(gpu.read(), np.uint8).reshape(h, w, 3)).tobytes()
    else:
        frame = old
    enc.stdin.write(frame)
enc.stdin.close()
enc.wait()
dec.wait()
print(f'patched {b - a + 1} frames in {time.time() - t0:.1f}s -> {out}')
