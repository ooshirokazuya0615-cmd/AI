#!/usr/bin/env bash
# Pack what the Pod needs into one file: the film's code (this folder's parent), the fonts it reads by
# absolute path, and the master audio. Run in the agent's sandbox:  bash bundle.sh OUT_DIR
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${1:?usage: bundle.sh OUT_DIR}
T=$(mktemp -d)
mkdir -p $T/code/tools/nonverbal/prototypes $T/fonts/inter $T/fonts/crosextra $T/fonts/freefont
cp -r "$HERE/.." $T/code/tools/nonverbal/prototypes/neon_machine
rm -rf $T/code/tools/nonverbal/prototypes/neon_machine/runpod/master_audio.flac
find $T/code -name __pycache__ -prune -exec rm -r {} +
cp /usr/share/fonts/opentype/inter/Inter-Regular.otf /usr/share/fonts/opentype/inter/Inter-SemiBold.otf $T/fonts/inter/
cp /usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf $T/fonts/crosextra/
cp /usr/share/fonts/truetype/freefont/FreeSerif.ttf /usr/share/fonts/truetype/freefont/FreeSerifBold.ttf \
   /usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf $T/fonts/freefont/
cp "$HERE/master_audio.flac" $T/master_audio.flac
mkdir -p "$OUT"
tar czf "$OUT/bundle.tgz" -C $T code fonts master_audio.flac
rm -rf $T
ls -la "$OUT/bundle.tgz"
