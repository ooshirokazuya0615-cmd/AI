"""
音をプログラムで作るための部品（numpy だけで動く）

音源ファイルは一切使いません。全部 sin 波と乱数から作るので、録音の権利は発生しません。
ただし旋律の権利は別です。使える曲の条件は POLICY.md を参照してください。
"""
import wave

import numpy as np

SR = 48000
TAU = 2 * np.pi


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _t(seconds):
    return np.arange(int(seconds * SR)) / SR


def _attack(sig, seconds=0.003):
    n = min(len(sig), max(1, int(seconds * SR)))
    sig[:n] *= np.linspace(0, 1, n)
    return sig


class Mix:
    """ステレオのミックスバス。音を好きな時刻・定位で足していく。"""

    def __init__(self, seconds):
        self.buf = np.zeros((int(seconds * SR) + 1, 2))

    def add(self, at, mono, pan=0.0, gain=1.0):
        i = int(round(at * SR))
        if i < 0:  # 頭が0秒より前にはみ出す音は、はみ出た分だけ切る
            mono, i = mono[-i:], 0
        n = min(len(mono), len(self.buf) - i)
        if n <= 0:
            return
        a = (np.clip(pan, -1, 1) + 1) * np.pi / 4  # 等パワーパン
        self.buf[i:i + n, 0] += mono[:n] * np.cos(a) * gain
        self.buf[i:i + n, 1] += mono[:n] * np.sin(a) * gain


# ---------- 音色 ----------

def bell(f, seconds=2.6, bright=1.0):
    """FM合成のベル／エレピ。叩いた瞬間だけ倍音が多く、すぐ丸くなる。"""
    t = _t(seconds)
    index = 2.8 * bright * np.exp(-t / 0.16)
    body = np.sin(TAU * f * t + index * np.sin(TAU * f * t))
    warm = 0.22 * np.sin(TAU * 2.0 * f * t) * np.exp(-t / 0.5)
    tine = 0.13 * bright * np.sin(TAU * min(f * 7.0, 7000) * t) * np.exp(-t / 0.012)
    decay = np.exp(-t / (0.7 + 260 / f))  # 低い音ほど長く響く
    return _attack((body + warm + tine) * decay)


def pad(freqs, seconds, fade=1.6):
    """ゆっくり立ち上がる和音のパッド。少しずつずらしたsin波を重ねて揺らぎを出す。"""
    t = _t(seconds)
    sig = np.zeros_like(t)
    rng = np.random.default_rng(len(freqs))
    for f in freqs:
        for cents in (-7, 0, 7):
            ff = f * 2 ** (cents / 1200)
            sig += np.sin(TAU * ff * t + rng.uniform(0, TAU))
            sig += 0.18 * np.sin(TAU * 2 * ff * t + rng.uniform(0, TAU))
    sig *= 1 + 0.15 * np.sin(TAU * 0.23 * t)
    n = min(int(fade * SR), len(t) // 2)
    env = np.ones_like(t)
    ramp = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n))
    env[:n], env[-n:] = ramp, ramp[::-1]
    return sig * env / (3 * len(freqs))


def thump(seconds=0.3, f0=130, f1=50):
    """ドスッという低音。ピッチを急に落としたsin波。"""
    t = _t(seconds)
    f = f1 + (f0 - f1) * np.exp(-t / 0.035)
    return _attack(np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / (seconds * 0.4)), 0.001)


def noise(seconds, lo, hi, seed=0):
    """lo〜hi Hz に帯域を絞ったノイズ（FFTで不要な帯域を消す）。"""
    n = int(seconds * SR)
    spec = np.fft.rfft(np.random.default_rng(seed).standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4) / (1 + (f / hi) ** 4)
    sig = np.fft.irfft(spec, n)
    return sig / (np.abs(sig).max() + 1e-9)


def riser(seconds, seed=0):
    """フィナーレ前の「シューッ」と上がっていく音。低い帯域から高い帯域へ移る。"""
    t = np.linspace(0, 1, int(seconds * SR))
    low, high = noise(seconds, 200, 1800, seed), noise(seconds, 1800, 11000, seed + 1)
    return (low * (1 - t) + high * t) * t ** 2.5


# ---------- 空間・仕上げ ----------

def reverb(buf, seconds=3.0, wet=0.25, seed=0):
    """減衰するノイズをインパルス応答にした畳み込みリバーブ（左右で別のノイズ）。"""
    n_ir = int(seconds * SR)
    t = np.arange(n_ir) / SR
    f = np.fft.rfftfreq(n_ir, 1 / SR)
    rng = np.random.default_rng(seed)
    pre = int(0.022 * SR)
    size = 1 << int(np.ceil(np.log2(len(buf) + n_ir + pre)))
    src = np.fft.rfft(buf.mean(axis=1), size)
    fs = np.fft.rfftfreq(size, 1 / SR)
    src /= 1 + (250 / np.maximum(fs, 1)) ** 2  # 低音は響かせない（濁りの元になる）
    out = buf.copy()
    for ch in (0, 1):
        ir = rng.standard_normal(n_ir) * np.exp(-t * 6.9 / seconds)
        ir = np.fft.irfft(np.fft.rfft(ir) / (1 + (f / 5500) ** 2), n_ir)  # 高音ほど早く消える
        ir = np.concatenate([np.zeros(pre), ir / np.sqrt(np.sum(ir ** 2))])
        tail = np.fft.irfft(src * np.fft.rfft(ir, size), size)[:len(buf)]
        out[:, ch] += wet * tail
    return out


def write_wav(path, buf):
    peak = np.abs(buf).max() + 1e-9
    x = np.tanh(buf / peak * 1.3) / np.tanh(1.3) * 0.92  # 軽くサチュレートして頭を丸める
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
