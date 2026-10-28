# 完成版を Runpod のGPUで1080pに書き出す手順（引き継ぎ用）

対象：炎のビー玉・20曲メドレー（4分58秒）。2026-10-28 にぱっちゃんが「これで完成させて」と決めた版。

## いまの状態（2026-10-28）

- 完成版のコード：コミット `834b7a6`（このフォルダの一つ上の `film8.py` / `overlay.py` / `songs7.py` ほか）。
  - 720pの確認用はぱっちゃんに送り済み。
- 音声：`master_audio.flac`（このフォルダ）。720p版と同じ音で、-14.3 LUFS、297.99秒。書き出し直しは不要。
- ぱっちゃんの判断：有料のクラウドGPU（Runpod）で1080pにする。
  - 見積もりは約300〜1,500円（RTX 4090 1台で6〜10時間、1時間0.34〜0.89ドル）。
  - 約束していること：本番の前に100コマ程度を試して、実際の速さと金額をぱっちゃんに日本語で報告してから全体を回す。
- 準備の状況：
  - Runpod のアカウント作成とAPIキーの保存は済み（環境変数 `RUNPOD_API_KEY`）。
  - 残高は2026-10-28時点で $0.00。始める前に残高を確認し、0なら右上の **Load credits** で10〜15ドルのチャージを頼む。
  - ネット接続は Full（runpod.io / runpod.net に届くことを確認済み）。
- このクラウド環境では、`/reload-plugins` と `/mcp` のサインインは使えない。なので、MCPではなくAPIキーで直接操作する。

## 守ること

- APIキーは表示しない・ファイルに書かない・チャットに出さない。`$RUNPOD_API_KEY` を参照するだけにする。
- Podは書き出しが終わったら（失敗したときも）すぐに止めて削除する。お金がかかり続けるため。
- ぱっちゃんへの報告はすべて日本語で、手順は1つずつ伝える。

## 流れ

### 1. 荷物を作る

```
bash tools/nonverbal/prototypes/neon_machine/runpod/bundle.sh $SCRATCH/rp     # → $SCRATCH/rp/bundle.tgz（約29MB）
```

中身は、コード・フォント（コードが絶対パスで読む Inter / Caladea / FreeSerif）・音声です。

### 2. Podを作る（RTX 4090、ディスク60GB以上）

- イメージ：python3 が入っていれば何でもよい（例：Runpod の PyTorch イメージ）。
  - Python 3.11 と bpy は、`pod_render.sh setup` が uv で入れる。
- 公開ポート：`8000/http`
- 環境変数：
  - `POD_TOKEN`：毎回ランダムに作る。`openssl rand -hex 16` など。
  - `BOOT`：`pod_server.py` を base64 にしたもの。
- 起動コマンド：

  ```
  bash -c 'echo $BOOT | base64 -d > /boot.py && exec python3 /boot.py'
  ```

- APIの書き方は Runpod の公式手順で確かめる（https://docs.runpod.io/ 、または公式プラグインの `runpodctl` / `pod-deploy` スキル）。
  - プラグインは次のコマンドで入る：
    ```
    claude plugin marketplace add runpod/runpod-plugins-official
    claude plugin install runpod@runpod
    ```
  - `runpodctl` も `RUNPOD_API_KEY` を読む。
- 在庫と値段は作る前に確かめる。RTX 4090 がなければ、同じくらいの速さのGPUを選ぶ。

### 3. つなぐ

```
URL=https://<pod-id>-8000.proxy.runpod.net
curl -s -H "X-Token: $POD_TOKEN" $URL/ping     # → ok
```

Pod が立ち上がるまで数分かかる。

### 4. 荷物を送って準備

荷物を送ってから、最初のジョブを投げる。`pod_render.sh` 自体が荷物の中にあるので、最初のジョブで展開してから `setup` を呼ぶ：

```
curl -s -H "X-Token: $POD_TOKEN" -T $SCRATCH/rp/bundle.tgz $URL/f/bundle.tgz
curl -s -H "X-Token: $POD_TOKEN" -X POST \
  --data-binary 'cd /work && tar xzf bundle.tgz && bash /work/code/tools/nonverbal/prototypes/neon_machine/runpod/pod_render.sh setup' \
  $URL/run
```

（`setup` の中でももう一度展開するが、上書きになるだけで問題ない。）

進み具合は次の2つで見る：

```
curl -s -H "X-Token: $POD_TOKEN" "$URL/log?n=40"
curl -s -H "X-Token: $POD_TOKEN" $URL/status
```

ログに `rendering on OPTIX [...]`（または CUDA）が出ることを、試しの段階で必ず確かめる。出なければCPUで描いていて、遅いうえにお金の無駄になる。

### 5. 試し（100コマ）→ ぱっちゃんに金額を報告

```
... /run に  bash /work/code/.../runpod/pod_render.sh render 1-120
```

- ログの `Time:` の値が1コマあたりの秒数。最初の1回だけ、場面の組み立てに数分かかる。
- 合計の見積もり ＝ 7,152コマ × 1コマの秒数 ÷ 3600 × 1時間の料金。円でも伝える。
- 参考：このサンドボックスのCPUでは、1080p・16サンプルで1コマ約75秒（2026-10-28に計測）。
  - そのうち約4秒は、GPUでは速くならない処理（場面の更新・合成・保存）。

### 6. 本番

```
... /run に  bash /work/code/.../runpod/pod_render.sh render 1-7152
```

- 途中で止まっても、同じコマンドで続きから書き出せる。
- 2台に分けるときは、範囲を分けて別のPodで回す。最後に1台に集めて、7で仕上げる。
- 監視は20〜30分おきでよい。こちらのセッションのバックグラウンド実行には2時間の上限があるので、待つ処理は2時間以内で区切る。

### 7. 仕上げ → 受け取る → Podを止める

```
... /run に  bash /work/code/.../runpod/pod_render.sh finish      # 文字を重ねる → 音と合わせて書き出す
curl -s -H "X-Token: $POD_TOKEN" -o $SCRATCH/full_film_1080p.mp4 $URL/f/out/full_film_1080p.mp4
```

- 受け取る前に、手元のディスクの空きを確認する（mp4は200MB前後の見込み）。
- 受け取ったらすぐにPodを止めて削除する。
- 確認すること：
  - 長さが約298秒
  - 1920x1080
  - 音量が約-14 LUFS
  - 数か所のコマを目で見る（冒頭・3択カード・最後のカード）
- mp4はリポジトリに入れない。

## このあとに残っていること

- サムネイルBの作り直し：
  - 壁の形が「縦に並んだページの塔」に変わったため。
  - 最後の全体の場面（フレーム7100前後）を1080p・32サンプルで描き、`thumb_compose.py` で「CAN YOU NAME / ALL 20?」を入れる。
- 概要欄の翻訳（DE / FR / NL / SV / JA）。
  - JA は `style/voice.md` を読んでから書く。
  - 概要欄とチャプターは `drafts/2026-10-25-公開用-タイトル概要欄チャプター.md`。
