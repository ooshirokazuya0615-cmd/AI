#!/usr/bin/env python3
"""
Bowling strike -> domino wave prototype.
  python3 build.py                        -> strike.mp4 (540x960 @ 60)
  python3 build.py --stills 0.5,1.6,5.0   -> PNGs of exact frames
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

import timeline as T  # noqa: E402


class Renderer:
    def __init__(self, gpu, w, h, fps):
        self.gpu, self.w, self.h, self.fps = gpu, w, h, fps
        src = (HERE / 'strike.glsl').read_text()
        self.scene = gpu.program(src.replace('//#define PASS', '#define SCENE_PASS'))
        self.bright = gpu.program(src.replace('//#define PASS', '#define BRIGHT_PASS'))
        self.post = gpu.program(src.replace('//#define PASS', '#define POST_PASS'))
        self.hdr = gpu.target('f2')
        self.brt = gpu.target('f2')
        self.brt.tex.build_mipmaps()
        self.pins = T.Pins()
        notes = T.note_dominoes()
        self.noteK = np.zeros(32)
        self.noteCol = np.zeros((32, 3))
        for i, nd in enumerate(notes):
            self.noteK[i] = nd['k']
            self.noteCol[i] = T.note_colour(nd['midi'])
        self.nNote = len(notes)
        self.kicks = [T.tm(b, s * 4) for b in range(4) for s in (0, 2)]
        self.frame_count = int(T.DURATION * fps)

    def uniforms(self, t):
        pos, basis = T.camera(t)
        bpos, dist = T.ball(t)
        ppos, prot = self.pins.state(t)
        pr = np.concatenate([m.flatten(order='F') for m in prot])
        fx = (T.env([T.T_STRIKE], t, 0.12), T.env([T.T_BOOM], t, 0.35), T.env(self.kicks, t, 0.12))
        sa, sb, head = T.stick_capsules(t)
        sc = dict(u_res=(float(self.w), float(self.h)), u_time=t, u_camPos=tuple(pos),
                  u_stA=sa.flatten(), u_stB=sb.flatten(), u_head=tuple(head),
                  u_camRot=basis.flatten(order='F'), u_tanH=0.42,
                  u_ballPos=tuple(bpos), u_ballRot=T.ball_rot(dist).flatten(order='F'),
                  u_pinPos=ppos.flatten(), u_pinRot=pr,
                  u_waveT=t - T.T_DOM0, u_bigA=T.big_angle(t), u_nNote=self.nNote,
                  u_noteK=self.noteK, u_noteCol=self.noteCol.flatten(), u_fx=fx)
        imp = 1.0 if 0 <= t - T.T_BOOM < 1.5 / self.fps else (0.5 if 0 <= t - T.T_STRIKE < 1.0 / self.fps else 0.0)
        post = dict(u_res=(float(self.w), float(self.h)), u_time=t, u_impact=imp)
        return sc, post

    def render(self, f):
        t = f / self.fps
        sc, post = self.uniforms(t)
        g = self.gpu
        g.draw(self.scene, self.hdr, sc)
        g.draw(self.bright, self.brt, {}, {'u_hdr': self.hdr.tex})
        self.brt.tex.build_mipmaps()
        g.draw(self.post, None, post, {'u_hdr': self.hdr.tex, 'u_bright': self.brt.tex})


def master(path):
    import audio
    import engine as E
    mix, gr = audio.render()
    raw = Path(path).with_suffix('.raw.wav')
    E.write_wav16(raw, mix)
    pr = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(raw), '-af',
                         'loudnorm=I=-14:TP=-1.5:print_format=json', '-f', 'null', '-'],
                        capture_output=True, text=True).stderr
    m = json.loads(pr[pr.rindex('{'):pr.rindex('}') + 1])
    gain = 10 ** ((-14.0 - float(m['input_i'])) / 20)
    peak = np.abs(mix).max() * gain
    if peak > 0.84:          # keep true peak under about -1.5 dBFS
        gain *= 0.84 / peak
    E.write_wav16(path, mix * gain)
    raw.unlink()
    return float(m['input_i']), gain, gr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--size', default='540x960')
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--out', default=str(HERE / 'strike.mp4'))
    ap.add_argument('--stills')
    ap.add_argument('--audio-only', action='store_true')
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
    li, gain, gr = master(wav)
    print(f'audio pre-norm {li:.1f} LUFS gain {20 * math.log10(gain):+.1f} dB', flush=True)
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(a.fps), '-i', '-',
           '-i', str(wav), '-vf', R.video_filters(),
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-profile:v', 'high',
           '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
           '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', a.out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(rd.frame_count):
        rd.render(f)
        ff.stdin.write(rd.gpu.read())
        if f % 60 == 0:
            el = time.time() - t0
            print(f'  frame {f}/{rd.frame_count}  {el:.0f}s elapsed', flush=True)
    ff.stdin.close()
    ff.wait()
    print(json.dumps(dict(frames=rd.frame_count, wall=time.time() - t0)))


if __name__ == '__main__':
    main()
