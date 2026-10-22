#!/usr/bin/env bash
# Final render of "300 Years of Music, One Marble" (film8 + songs7), resumable.
#
#   PY=<python with bpy> [GPU=1] ./render_final.sh frames OUT_DIR [FIRST-LAST]
#       renders 1080p frames into OUT_DIR/frames; frames already on disk are kept, and empty
#       placeholders left by an interrupted run are removed first, so the same command resumes.
#       With Blender itself instead of the bpy module: PY="blender -b -P" works the same way.
#   VSCO_DIR=<samples> ./render_final.sh finish OUT_DIR
#       sound (piano + tube and tap events), overlay cards and film finish, then the final mp4.
set -euo pipefail
cd "$(dirname "$0")"
cmd=$1; OUT=$2; shift 2
FPS=${FPS:-24}; RES=${RES:-1920x1080}; SAMPLES=${SAMPLES:-16}
PY=${PY:-python3}
export SONGS_MODULE=songs7
mkdir -p "$OUT/frames"

case "$cmd" in
frames)
    RANGE=${1:-}
    GPUFLAG=$([ -n "${GPU:-}" ] && echo --gpu || true)
    find "$OUT/frames" -name 'f_*.png' -size 0 -delete
    if [ -z "$RANGE" ]; then
        N=$(EVENTS_ONLY=1 EVENTS_OUT="$OUT/events.json" $PY film8.py -- --res "$RES" --fps "$FPS" \
            --out "$OUT/frames/f_" 2>/dev/null | awk '/frames total/ {print $3}')
        RANGE="1-$N"
    fi
    echo "frames $RANGE at $RES, $SAMPLES samples, $FPS fps $GPUFLAG"
    $PY film8.py -- --res "$RES" --samples "$SAMPLES" --fps "$FPS" --out "$OUT/frames/f_" \
        --frames "$RANGE" $GPUFLAG
    ;;
finish)
    EVENTS_ONLY=1 EVENTS_OUT="$OUT/events.json" $PY film8.py -- --res "$RES" --fps "$FPS" --out "$OUT/frames/f_" >/dev/null
    VOICE_SET=piano EVENTS_IN="$OUT/events.json" python3 audio6.py "$OUT/audio.wav"
    mkdir -p "$OUT/graded"
    python3 overlay.py "$OUT/frames" "$OUT/graded" --film --fps "$FPS"
    ffmpeg -y -loglevel error -framerate "$FPS" -i "$OUT/graded/f_%04d.png" -i "$OUT/audio.wav" \
        -c:v libx264 -preset slow -pix_fmt yuv420p -crf 17 -c:a aac -b:a 256k -shortest \
        -movflags +faststart "$OUT/300-years-of-music-one-marble.mp4"
    echo "wrote $OUT/300-years-of-music-one-marble.mp4"
    ;;
*)
    echo "usage: $0 frames|finish OUT_DIR ..." >&2; exit 2 ;;
esac
