#!/usr/bin/env python3
"""
Score-first 音ハメ prototype.
  python3 build.py                       -> otohame.mp4 (540x960 @ 60)
  python3 build.py --stills 0.3,0.5,2.5  -> PNGs of exact frames (stateless render)
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
import render as R  # noqa: E402  (repo GPU wrapper, used read-only)

import choreo as C  # noqa: E402
import engine as E  # noqa: E402
import score as S  # noqa: E402

BODY = (1.0, 0.50, 0.12)
NB = 20


class Renderer:
    def __init__(self, gpu, w, h, fps):
        self.gpu, self.w, self.h, self.fps = gpu, w, h, fps
        src = (HERE / 'otohame.glsl').read_text()
        self.scene = gpu.program(src.replace('//#define PASS', '#define SCENE_PASS'))
        self.bright = gpu.program(src.replace('//#define PASS', '#define BRIGHT_PASS'))
        self.post = gpu.program(src.replace('//#define PASS', '#define POST_PASS'))
        self.hdr = gpu.target('f2')
        self.brt = gpu.target('f2')
        mgl = gpu.mgl
        self.brt.tex.build_mipmaps()
        self.brt.tex.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)
        self.ch = C.Choreo()
        assert len(self.ch.blocks) <= NB
        self.conf = C.Confetti(np.array([self.ch.lands[-1]['x'], C.height(81) + C.R, 0.0]), self.ch.final_t)
        self.frame_count = int(round(S.DURATION * fps))
        self.log = []

    def uniforms(self, t):
        ch = self.ch
        pos, tgt, fov, roll, shot = ch.camera(t)
        basis = ch.cam_basis(pos, tgt, roll)
        tanh_ = math.tan(math.radians(fov) / 2)
        b = ch.body(t, pos)
        blk = np.zeros((NB, 4))
        fx = np.zeros((NB, 4))
        fx[:, 3] = -1
        col = np.zeros((NB, 3))
        landx = np.zeros(NB)
        rows = ch.block_fx(t)
        for i, bl in enumerate(ch.blocks):
            blk[i] = (bl['x0'], bl['x1'], bl['top'] - ch.dip(i, t), C.DEPTH)
            fx[i] = rows[i]
            col[i] = bl['col']
        for l in ch.lands:
            landx[l['b']] = l['x']
        drum = (ch.env(ch.kicks, t, 0.12), ch.env(ch.snares, t, 0.16),
                ch.env(np.array([e[0] for e in S.drum_events()['hat']]), t, 0.05))
        fin = t - ch.final_t if t >= ch.final_t else -1.0
        sc = dict(u_res=(float(self.w), float(self.h)), u_camPos=tuple(pos),
                  u_camRot=basis.flatten(order='F'), u_tanH=tanh_,
                  u_cPos=tuple(b['center']), u_cRot=b['rot'].flatten(order='F'), u_cRad=tuple(b['rad']),
                  u_cR=C.R, u_face=(b['squint'], b['blink'], b['mouth'], b['happy']), u_look=tuple(b['look']),
                  u_bodyCol=BODY, u_bounce=tuple(b['bounce']), u_nBlk=len(ch.blocks), u_blk=blk, u_blkFx=fx, u_blkCol=col,
                  u_landX=landx, u_drum=drum, u_final=fin, u_time=t)
        # confetti projected to screen
        conf = np.zeros((48, 4))
        ccol = np.zeros((48, 4))
        n = 0
        st = self.conf.at(t)
        if st is not None:
            P, ang, size, cc, alpha = st
            for k in range(len(P)):
                d = P[k] - pos
                xc, yc, zc = d @ basis[:, 0], d @ basis[:, 1], d @ basis[:, 2]
                if zc < 0.15 or n >= 48:
                    continue
                uvx, uvy = xc / zc / tanh_, yc / zc / tanh_
                conf[n] = ((uvx * self.h + self.w) / 2, (uvy * self.h + self.h) / 2, ang[k],
                           size[k] / zc / tanh_ * self.h / 2)
                ccol[n] = (*cc[k], alpha)
                n += 1
        imp = 1.0 if 0 <= t - ch.final_t < 0.5 / self.fps else 0.0
        post = dict(u_res=(float(self.w), float(self.h)), u_time=t, u_nConf=n, u_conf=conf, u_confCol=ccol, u_impact=imp)
        return sc, post, dict(t=t, shot=shot, kind=b['kind'], s=b['s'], foot=b['foot'].tolist())

    def render(self, f):
        t = f / self.fps
        sc, post, info = self.uniforms(t)
        g = self.gpu
        g.draw(self.scene, self.hdr, sc)
        g.draw(self.bright, self.brt, {}, {'u_hdr': self.hdr.tex})
        self.brt.tex.build_mipmaps()
        g.draw(self.post, None, post, {'u_hdr': self.hdr.tex, 'u_bright': self.brt.tex})
        self.log.append(info)


def master(path):
    mix, gr = S.render_audio()
    raw = Path(path).with_suffix('.raw.wav')
    E.write_wav16(raw, mix)
    pr = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(raw), '-af',
                         'loudnorm=I=-14:TP=-1.5:print_format=json', '-f', 'null', '-'],
                        capture_output=True, text=True).stderr
    m = json.loads(pr[pr.rindex('{'):pr.rindex('}') + 1])
    gain = 10 ** ((-14.0 - float(m['input_i'])) / 20)
    E.write_wav16(path, mix * gain)
    raw.unlink()
    return float(m['input_i']), gain, gr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--size', default='540x960')
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--out', default=str(HERE / 'otohame.mp4'))
    ap.add_argument('--stills')
    ap.add_argument('--tag', default='')
    a = ap.parse_args()
    w, h = (int(v) for v in a.size.split('x'))
    gpu = R.Gpu(w, h)
    print('GPU:', gpu.renderer, flush=True)
    rd = Renderer(gpu, w, h, a.fps)

    if a.stills:
        outdir = HERE / 'frames'
        outdir.mkdir(exist_ok=True)
        for ts in a.stills.split(','):
            f = int(round(float(ts) * a.fps))
            rd.render(f)
            png = outdir / f'still{a.tag}-{f / a.fps:05.2f}s.png'
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo',
                            '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-i', '-', '-vf', 'vflip',
                            '-frames:v', '1', str(png)], input=gpu.read(), check=True)
            print(png, flush=True)
        return

    wav = HERE / 'audio.wav'
    t0 = time.time()
    li, gain, gr = master(wav)
    print(f'audio: {time.time() - t0:.1f}s  pre-norm {li:.1f} LUFS  gain {20 * math.log10(gain):+.1f} dB  '
          f'limiter max GR {20 * math.log10(max(1 - gr, 1e-9)):.2f} dB', flush=True)

    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(a.fps), '-i', '-',
           '-i', str(wav), '-vf', R.video_filters(),
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-profile:v', 'high',
           '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
           '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', a.out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    times = []
    t0 = time.time()
    for f in range(rd.frame_count):
        ts = time.time()
        rd.render(f)
        data = gpu.read()
        times.append(time.time() - ts)
        ff.stdin.write(data)
        if f % 60 == 0:
            print(f'  frame {f}/{rd.frame_count}  {1 / np.mean(times[-60:]):.2f} fps', flush=True)
    ff.stdin.close()
    ff.wait()
    tot = time.time() - t0
    stats = dict(frames=rd.frame_count, wall=tot, render_fps=rd.frame_count / tot,
                 gpu_fps=1 / np.mean(times), slowest_frame=max(times), size=[w, h], fps=a.fps)
    (HERE / 'render_stats.json').write_text(json.dumps(stats, indent=1))
    (HERE / 'anim_log.json').write_text(json.dumps(rd.log))
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
