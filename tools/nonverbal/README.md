# ノンバーバル動画ツール

セリフも文字もない「見ているだけで気持ちいい」動画を、**コードだけ**で作ります。

```
python3 tools/nonverbal/render.py bounce_ring
```

| 担当 | 中身 |
|---|---|
| 映像 | GLSL シェーダーで **GPU 描画**（`scenes/*.glsl`）|
| 音 | numpy で **波形から合成**（`synth.py`）。音源ファイルは一切使わない |
| 動き | Python で物理シミュレーション（`scenes/*.py`）|
| 書き出し | ffmpeg で MP4（H.264 + AAC、YouTube向けの色・音量）|

映像の動きと音は、同じシミュレーション結果から作るので**ズレません**。
ボールが跳ねた瞬間に、必ずその音が鳴ります。

Claude Code に「ノンバーバル動画を1本作って」と言えば、書き出しまで全部やります。

## 準備

```
pip install -r tools/nonverbal/requirements.txt
```

ffmpeg も必要です（Mac なら `brew install ffmpeg`）。

GPU がない環境（クラウドなど）では、CPU が GPU の代わりをします。
遅くなるだけで、できあがる映像は同じです。
画面のない Linux では `xvfb-run` を使って自動で起動し直します。

## オプション

| オプション | 説明 |
|---|---|
| `-o 出力先.mp4` | 省略時は `drafts/videos/日付-nonverbal-シーン名.mp4` |
| `--seconds 40` | 動画の長さの目安。シーンがこの長さに収まるよう動きを調整する |
| `--size 1080x1920` | 解像度。Shorts は `1080x1920`、横長は `1920x1080` |
| `--fps 60` | フレームレート |
| `--seed 1` | 乱数の種。**変えると別の動き・別のメロディになる**。量産はこれを変えるだけ |
| `--preview` | 半分の解像度・30fps で素早く確認する |
| `--still 2,15,38` | 動画の代わりに、指定した秒の静止画を書き出す（サムネ用にも使える）|

## シーン

### `bounce_ring`

リングの中でボールが跳ねる。跳ねるたびに少し大きくなり、色が変わり、音がひとつ鳴る。
跳ねる間隔はだんだん短くなり、最後はリングいっぱいになって弾ける。

- 音はコード進行 Am–F–C–G の上を行き来するアルペジオ。どこで跳ねても和音から外れない
- 最後だけ C add9 の和音で、開放的に終わる
- `--seconds` に合わせて「1回あたりの成長量」を自動で探すので、狙った長さで弾ける

## 音について

- **音源ファイルを使っていない**ので、著作権・Content ID の心配がない完全オリジナルです
- 音量は YouTube の基準（-14 LUFS / -1.5 dBTP）に自動で揃えます

## 新しいシーンを足す

`scenes/<名前>.py` に `Scene` クラスを書き、必要なら同じ名前の `.glsl` を置きます。

```python
class Scene:
    def __init__(self, gpu, cfg):   # cfg.width / height / fps / seconds / seed
        self.frame_count = ...       # 総フレーム数
    def render(self, f):             # f フレーム目を gpu.draw(...) で描く
        ...
    def audio(self):                 # (サンプル数, 2) の numpy 配列。48kHz
        ...
```

| `gpu` のメソッド | 用途 |
|---|---|
| `gpu.program(glsl)` | フラグメントシェーダーを読み込む |
| `gpu.target()` | 残像などに使う、前のフレームを覚えておくためのテクスチャ |
| `gpu.draw(program, target, uniforms, textures)` | 描く。`target=None` で画面（＝動画のフレーム）に描く |

音の部品（`synth.py`）：`bell`（FMベル）、`pad`（和音の伸ばし）、`thump`（低音の一撃）、
`noise`（帯域を絞ったノイズ）、`riser`（盛り上げ）、`reverb`（残響）、`Mix`（ミックス）。
