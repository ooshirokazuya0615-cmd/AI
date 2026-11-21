#!/usr/bin/env python3
"""
ノンバーバル動画（セリフなし・文字なし）の生成ツール

  python3 tools/nonverbal/render.py <シーン名> [オプション]

映像は GLSL シェーダーで GPU 描画、音は numpy で波形から合成、
最後に ffmpeg で MP4（H.264 + AAC）にまとめます。
仕様は tools/nonverbal/README.md を参照。
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import synth  # noqa: E402

VERT = """
#version 330
in vec2 in_pos;
out vec2 v_uv;
void main() {
    v_uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""


@dataclass
class Config:
    width: int
    height: int
    fps: int
    seconds: float
    seed: int


# ---------- GPU ----------

def create_context():
    import moderngl

    errors = []
    for kw in ({}, {'backend': 'egl'}):
        try:
            return moderngl.create_standalone_context(require=330, **kw)
        except Exception as e:  # 環境によって使えるバックエンドが違う
            errors.append(f'{kw or "default"}: {e}')

    # 画面のないLinux（クラウド等）では仮想ディスプレイ上で自分を起動し直す
    if not os.environ.get('NONVERBAL_IN_XVFB') and shutil.which('xvfb-run'):
        os.environ['NONVERBAL_IN_XVFB'] = '1'
        os.execvp('xvfb-run', ['xvfb-run', '-a', '-s', '-screen 0 640x480x24',
                               sys.executable, *sys.argv])
    raise SystemExit('OpenGL を初期化できませんでした。\n  ' + '\n  '.join(errors))


class Pass:
    def __init__(self, prog, vao):
        self.prog, self.vao = prog, vao


class Target:
    def __init__(self, tex, fbo):
        self.tex, self.fbo = tex, fbo


class Gpu:
    """全画面に1枚の四角形を描き、フラグメントシェーダーで全ピクセルを塗る。"""

    def __init__(self, width, height):
        import moderngl
        self.mgl = moderngl
        self.ctx = create_context()
        self.size = (width, height)
        self.vbo = self.ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], 'f4').tobytes())
        self.out = self.ctx.framebuffer(color_attachments=[self.ctx.renderbuffer(self.size, 4)])

    @property
    def renderer(self):
        return self.ctx.info['GL_RENDERER']

    def program(self, frag):
        prog = self.ctx.program(vertex_shader=VERT, fragment_shader=frag)
        return Pass(prog, self.ctx.vertex_array(prog, [(self.vbo, '2f', 'in_pos')]))

    def target(self, dtype='f2'):
        """フィードバック（残像など）用の浮動小数テクスチャ。"""
        tex = self.ctx.texture(self.size, 4, dtype=dtype)
        tex.filter = (self.mgl.LINEAR, self.mgl.LINEAR)
        tex.repeat_x = tex.repeat_y = False
        fbo = self.ctx.framebuffer(color_attachments=[tex])
        fbo.clear(0, 0, 0, 0)
        return Target(tex, fbo)

    def draw(self, p, target=None, uniforms=None, textures=None):
        (target.fbo if target else self.out).use()
        for unit, (name, tex) in enumerate((textures or {}).items()):
            tex.use(unit)
            if name in p.prog:
                p.prog[name].value = unit
        for name, value in (uniforms or {}).items():
            if name not in p.prog:  # シェーダー側で使われていない uniform は最適化で消える
                continue
            if isinstance(value, np.ndarray):
                p.prog[name].write(value.astype('f4').tobytes())
            else:
                p.prog[name].value = value
        p.vao.render(self.mgl.TRIANGLE_STRIP)

    def read(self):
        return self.out.read(components=3, alignment=1)


# ---------- 音 ----------

def master_audio(mix, path, lufs=-14.0):
    """YouTube基準（-14 LUFS / -1.5 dBTP）にラウドネスを揃えて WAV に書く。"""
    raw = Path(path).with_suffix('.raw.wav')
    synth.write_wav(raw, mix)
    probe = subprocess.run(
        ['ffmpeg', '-hide_banner', '-nostats', '-i', str(raw),
         '-af', f'loudnorm=I={lufs}:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
        capture_output=True, text=True, check=True).stderr
    m = json.loads(probe[probe.rindex('{'):probe.rindex('}') + 1])
    af = (f'loudnorm=I={lufs}:TP=-1.5:LRA=11:linear=true'
          f':measured_I={m["input_i"]}:measured_TP={m["input_tp"]}'
          f':measured_LRA={m["input_lra"]}:measured_thresh={m["input_thresh"]}'
          f':offset={m["target_offset"]}')
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(raw),
                    '-af', af, '-ar', str(synth.SR), str(path)], check=True)
    raw.unlink()


# ---------- 書き出し ----------

def load_scene(name):
    path = HERE / 'scenes' / f'{name}.py'
    if not path.exists():
        names = sorted(p.stem for p in (HERE / 'scenes').glob('*.py') if not p.stem.startswith('_'))
        raise SystemExit(f'シーン "{name}" がありません。使えるシーン: {", ".join(names)}')
    spec = importlib.util.spec_from_file_location(f'scenes.{name}', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def video_filters():
    # OpenGL は左下原点なので上下反転。色はYouTubeが前提とするBT.709で書き出す
    return 'vflip,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p'


def encode(scene, gpu, cfg, out, audio_path, quality):
    w, h = cfg.width, cfg.height
    crf, preset = {'final': (18, 'slow'), 'preview': (24, 'veryfast')}[quality]
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(cfg.fps), '-i', '-',
           '-i', str(audio_path),
           '-vf', video_filters(),
           '-c:v', 'libx264', '-preset', preset, '-crf', str(crf), '-profile:v', 'high',
           '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
           '-c:a', 'aac', '-b:a', '192k',
           '-movflags', '+faststart', '-shortest', str(out)]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frames = scene.frame_count
    t0 = time.time()
    for f in range(frames):
        scene.render(f)
        ff.stdin.write(gpu.read())
        if f % cfg.fps == 0 or f == frames - 1:
            done = (f + 1) / frames
            eta = (time.time() - t0) / done * (1 - done)
            print(f'\r  映像 {f + 1}/{frames} フレーム  残り約{eta:4.0f}秒', end='', flush=True)
    print()
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit('ffmpeg のエンコードに失敗しました')


def stills(scene, gpu, cfg, out, times):
    """指定秒のフレームをPNGで書き出す（残像があるので頭から順に描く）。"""
    want = {min(int(round(t * cfg.fps)), scene.frame_count - 1): t for t in times}
    stem = Path(out).with_suffix('')
    for f in range(max(want) + 1):
        scene.render(f)
        if f in want:
            png = f'{stem}-{want[f]:05.2f}s.png'
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{cfg.width}x{cfg.height}',
                            '-i', '-', '-vf', 'vflip', '-frames:v', '1', png],
                           input=gpu.read(), check=True)
            print(f'  {png}')


def main():
    ap = argparse.ArgumentParser(description='ノンバーバル動画を書き出す')
    ap.add_argument('scene', help='tools/nonverbal/scenes/ のシーン名（例: bounce_ring）')
    ap.add_argument('-o', '--out', help='出力先 .mp4（省略時は drafts/videos/日付-nonverbal-シーン名.mp4）')
    ap.add_argument('--seconds', type=float, default=40, help='動画の長さの目安（秒）')
    ap.add_argument('--size', default='1080x1920', help='解像度（Shortsは1080x1920、横長は1920x1080）')
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--seed', type=int, default=1, help='乱数の種。変えると別の動きになる')
    ap.add_argument('--preview', action='store_true', help='半分の解像度・30fpsで素早く確認する')
    ap.add_argument('--still', help='動画の代わりに指定秒の静止画を書き出す（例: 2,15,38）')
    a = ap.parse_args()

    w, h = (int(v) for v in a.size.lower().split('x'))
    fps = a.fps
    if a.preview:
        w, h, fps = w // 2, h // 2, 30
    cfg = Config(width=w, height=h, fps=fps, seconds=a.seconds, seed=a.seed)

    out = Path(a.out) if a.out else (
        HERE.parent.parent / 'drafts' / 'videos' /
        f'{time.strftime("%Y-%m-%d")}-nonverbal-{a.scene.replace("_", "-")}.mp4')
    out.parent.mkdir(parents=True, exist_ok=True)

    gpu = Gpu(w, h)
    print(f'GPU: {gpu.renderer}')
    if 'llvmpipe' in gpu.renderer or 'softpipe' in gpu.renderer:
        print('  ※ GPUが見つからないため CPU で代わりに描画します（遅いですが結果は同じです）')

    scene = load_scene(a.scene).Scene(gpu, cfg)
    print(f'シーン: {a.scene}  {w}x{h} {fps}fps  {scene.frame_count / fps:.1f}秒')

    if a.still:
        stills(scene, gpu, cfg, out, [float(t) for t in a.still.split(',')])
        return

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / 'audio.wav'
        print('  音を合成中…')
        master_audio(scene.audio(), wav)
        encode(scene, gpu, cfg, out, wav, 'preview' if a.preview else 'final')
    print(f'書き出し: {out}  ({out.stat().st_size / 1e6:.1f} MB)')


if __name__ == '__main__':
    main()
