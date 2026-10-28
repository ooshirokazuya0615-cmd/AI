#!/usr/bin/env bash
# The finished film at 1080p on a rented GPU Pod. Runs on the Pod in /work, after bundle.tgz is uploaded.
#   bash pod_render.sh setup            libraries, Python 3.11 + bpy, the fonts the film and overlay use
#   bash pod_render.sh render 1-200     render frames A-B (resumable: frames already on disk are skipped)
#   bash pod_render.sh finish           overlay every frame, then encode with the master audio
# Settings: SAMPLES (default 16), RES (default 1920x1080)
set -euo pipefail
W=/work
CODE=$W/code/tools/nonverbal/prototypes/neon_machine
PY=$W/venv/bin/python
SAMPLES=${SAMPLES:-16}
RES=${RES:-1920x1080}

case "${1:-}" in
setup)
  cd $W && tar xzf bundle.tgz
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq libxrender1 libxxf86vm1 libxfixes3 libxi6 libxkbcommon0 libsm6 libgl1 libegl1 \
    libglib2.0-0 ffmpeg > /dev/null
  for d in opentype/inter truetype/crosextra truetype/freefont; do      # the exact paths the code reads
    mkdir -p /usr/share/fonts/$d && cp -n $W/fonts/$(basename $d)/* /usr/share/fonts/$d/
  done
  command -v uv > /dev/null || pip install -q uv
  uv venv -q -p 3.11 $W/venv
  uv pip install -q -p $PY bpy==4.5.14 numpy==1.26.4 pillow
  $PY -c "import bpy; print('bpy', bpy.app.version_string)"
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
  ;;
render)
  mkdir -p $W/fr
  find $W/fr -name '*.png' -size 0 -delete
  cd $CODE
  SONGS_MODULE=songs7 $PY -u film8.py -- --res $RES --samples $SAMPLES --fps 24 --gpu \
    --out $W/fr/f_ --frames "$2"
  echo "rendered $(find $W/fr -name '*.png' -size +0 | wc -l) frames"
  ;;
finish)
  cd $CODE
  mkdir -p $W/g $W/out
  SONGS_MODULE=songs7 $PY overlay.py $W/fr $W/g --fps 24 --film
  n=$(ls $W/g | wc -l)
  ffmpeg -y -loglevel error -framerate 24 -start_number 1 -i $W/g/f_%04d.png -i $W/master_audio.flac \
    -frames:v $n -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p \
    -c:a aac -b:a 256k -shortest -movflags +faststart $W/out/full_film_1080p.mp4
  ls -la $W/out
  ;;
*)
  echo "usage: pod_render.sh setup | render A-B | finish"; exit 2 ;;
esac
