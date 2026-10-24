#!/usr/bin/env python3
"""KAKU & RONDO #2 Square Track.
  python3 build.py                     -> kaku.mp4
  python3 build.py --stills 0.5,4.0    -> frames/still-*.png
"""
import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, '/home/user/AI/tools/nonverbal')
import render as R  # noqa: E402

import camera as C  # noqa: E402
import rig  # noqa: E402
import timeline as T  # noqa: E402


class Renderer:
    def __init__(self, gpu, w, h, fps):
        self.gpu, self.w, self.h, self.fps = gpu, w, h, fps
        src = (HERE / 'kaku.glsl').read_text()
        self.scene = gpu.program(src.replace('//#define PASS', '#define SCENE_PASS'))
        self.bright = gpu.program(src.replace('//#define PASS', '#define BRIGHT_PASS'))
        self.post = gpu.program(src.replace('//#define PASS', '#define POST_PASS'))
        self.hdr = gpu.target('f2')
        self.brt = gpu.target('f2')
        self.brt.tex.build_mipmaps()
        self.grid = gpu.ctx.texture((T.GRID, T.GRID), 4, dtype='f4')
        self.grid.filter = (gpu.mgl.NEAREST, gpu.mgl.NEAREST)
        self.frame_count = int(round(T.DURATION * fps))
        self.ticks = [(tk, T.rondo(tk)[0]) for tk in T.rondo_ticks()]

    def uniforms(self, t):
        pos, basis, fov = C.camera(t)
        kc, kr, _ = T.kaku(t)
        kn, t1, t2 = T.knot(t)
        rpos, rdir, ang = T.rondo(t)
        axis = np.cross(np.array([0.0, 1.0, 0.0]), rdir)
        axis /= np.linalg.norm(axis) + 1e-9
        n0 = rdir
        rn = n0 * math.cos(ang) + np.array([0.0, 1.0, 0.0]) * math.sin(ang)    # turns about the rolling axis
        lx, lz, lb = T.fork_look(t)
        glow, fin = T.section_glow(t)
        j = T.starter(t)
        sa = np.array([j[s[0]] for s in rig.SEGS])
        sb = np.array([j[s[1]] for s in rig.SEGS])
        ma, mb = T.mallet(j)
        self.grid.write(T.grid_data(t).tobytes())
        dots = np.full((16, 3), -1.0)
        recent = [(tk, p) for tk, p in self.ticks if 0 <= t - tk < 1.5 and t < T.T_RESET][-16:]
        for i, (tk, p) in enumerate(recent):
            dots[i] = (p[0], p[2], t - tk)
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t / T.BEAT) if T.tb(24) <= t < T.tb(28) else 0.0
        hes = min(max((t - T.T_HES0) / (T.T_HES1 - T.T_HES0), 0.0), 1.0) if T.T_HES0 <= t < T.tb(29) else -1.0
        sc = dict(u_res=(float(self.w), float(self.h)), u_time=t, u_camPos=tuple(pos),
                  u_camRot=basis.flatten(order='F'), u_tanH=fov,
                  u_kC=tuple(kc), u_kR=kr.flatten(order='F'), u_knot=tuple(kn), u_tail1=tuple(t1), u_tail2=tuple(t2),
                  u_rP=tuple(rpos), u_rN=tuple(rn), u_look=(lx, lz, lb),
                  u_glow=np.array(glow), u_fin=float(fin),
                  u_stA=sa.flatten(), u_stB=sb.flatten(), u_head=tuple(j['head']),
                  u_malA=tuple(ma), u_malB=tuple(mb), u_metro=T.metronome(t),
                  u_board=T.board(t), u_startAge=(t - T.T_START) if t >= T.T_START else -1.0,
                  u_fpFade=T.fp_fade(t), u_finAge=(t - T.T_FINISH_K) if t >= T.T_FINISH_K else -1.0,
                  u_score=(pulse, hes), u_rDots=dots.flatten())
        imp = 1.0 if 0 <= t - T.T_FINISH_K < 2.5 / self.fps else 0.0
        post = dict(u_res=(float(self.w), float(self.h)), u_time=t, u_impact=imp)
        return sc, post

    def render(self, f):
        t = f / self.fps
        sc, post = self.uniforms(t)
        g = self.gpu
        g.draw(self.scene, self.hdr, sc, {'u_grid': self.grid})
        g.draw(self.bright, self.brt, {}, {'u_hdr': self.hdr.tex})
        self.brt.tex.build_mipmaps()
        g.draw(self.post, None, post, {'u_hdr': self.hdr.tex, 'u_bright': self.brt.tex})


def master(path):
    """-14 LUFS with a +3 dB shelf at 4 kHz, then an oversampled limiter at -2 dBTP."""
    import audio
    import engine as E
    mix = audio.render()
    raw = Path(path).with_suffix('.raw.wav')
    shelf = Path(path).with_suffix('.shelf.wav')
    E.write_wav16(raw, mix)
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(raw), '-af',
                    'highshelf=f=4000:g=3,equalizer=f=3000:t=q:w=0.8:g=4', '-c:a', 'pcm_f32le', str(shelf)], check=True)
    gain_db = 0.0
    for _ in range(3):
        pr = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(shelf), '-af',
                             f'volume={gain_db}dB,aresample=192000,alimiter=limit=0.79:attack=1:release=60:level=disabled:latency=1,'
                             'aresample=48000,ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
        li = float(pr[pr.rindex('I:'):].split()[1])
        gain_db += -14.0 - li
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(shelf), '-af',
                    f'volume={gain_db}dB,aresample=192000,alimiter=limit=0.79:attack=1:release=60:level=disabled:latency=1,aresample=48000',
                    '-c:a', 'pcm_s16le', str(path)], check=True)
    raw.unlink()
    shelf.unlink()
    return -14.0, 10 ** (gain_db / 20)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--size', default='540x960')
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--out', default=str(HERE / 'kaku.mp4'))
    ap.add_argument('--stills')
    ap.add_argument('--audio-only', action='store_true')
    ap.add_argument('--start', type=float, default=0.0)
    ap.add_argument('--end', type=float, default=None)
    a = ap.parse_args()
    if a.audio_only:
        print(master(HERE / 'audio.wav'))
        return
    w, h = (int(v) for v in a.size.split('x'))
    gpu = R.Gpu(w, h)
    print('GPU:', gpu.renderer, flush=True)
    rd = Renderer(gpu, w, h, a.fps)
    if a.stills:
        outdir = HERE / 'frames'
        outdir.mkdir(exist_ok=True)
        for ts in a.stills.split(','):
            f = int(round(float(ts) * a.fps))
            t0 = time.time()
            rd.render(f)
            png = outdir / f'still-{f / a.fps:05.2f}s.png'
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo',
                            '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-i', '-', '-vf', 'vflip',
                            '-frames:v', '1', str(png)], input=gpu.read(), check=True)
            print(png, f'{time.time() - t0:.2f}s', flush=True)
        return
    wav = HERE / 'audio.wav'
    li, gain = master(wav)
    print(f'audio pre-norm {li:.1f} LUFS gain {20 * math.log10(gain):+.1f} dB', flush=True)
    f0 = int(round(a.start * a.fps))
    f1 = rd.frame_count if a.end is None else int(round(a.end * a.fps))
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(a.fps), '-i', '-',
           '-ss', f'{f0 / a.fps:.4f}', '-i', str(wav), '-vf', R.video_filters(),
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-profile:v', 'high',
           '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
           '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', a.out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(f0, f1):
        rd.render(f)
        ff.stdin.write(rd.gpu.read())
        if f % 60 == 0:
            print(f'  frame {f}/{f1}  {time.time() - t0:.0f}s elapsed', flush=True)
    ff.stdin.close()
    ff.wait()
    print(json.dumps(dict(frames=f1 - f0, wall=time.time() - t0)))


if __name__ == '__main__':
    main()
