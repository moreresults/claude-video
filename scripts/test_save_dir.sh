#!/usr/bin/env bash
# Demo test: prove that watch.py + --save-dir produces a sanitised
# UCID-NNNN folder. Generates a 5-second synthetic video with ffmpeg
# (no download, no API key needed), runs the full pipeline against a
# temporary save-dir, and asserts the resulting folder matches the
# canonical naming format.

set -euo pipefail

REPO=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
SAVE_DIR="$TMP/save"
mkdir -p "$SAVE_DIR"
trap 'rm -rf "$TMP"' EXIT

# 1. Pre-seed the save-dir with a fake earlier UCID so we can verify the
#    auto-increment scans existing folders (not just starts at 0001).
mkdir -p "$SAVE_DIR/UCID-0099 2020-01-01 Pre-existing dummy"

# 2. Synthesise a short test video — no network, no API.
VIDEO="$TMP/demo with (parens) & ampersand!.mp4"
ffmpeg -nostdin -loglevel error -y \
  -f lavfi -i "testsrc=duration=3:size=320x180:rate=10" \
  -c:v libx264 -pix_fmt yuv420p "$VIDEO"

# 3. Run the actual /watch pipeline against it.
python3 "$REPO/scripts/watch.py" "$VIDEO" \
  --save-dir "$SAVE_DIR" \
  --no-whisper \
  --max-frames 3 \
  --resolution 256 \
  --hires-resolution 320 \
  >"$TMP/watch.stdout" 2>"$TMP/watch.stderr"

# 4. Locate the produced folder and assert its name.
SHOPT_SAVED=$(shopt -p nullglob || true)
shopt -s nullglob
PRODUCED=("$SAVE_DIR"/UCID-*/)
eval "$SHOPT_SAVED"

if [ ${#PRODUCED[@]} -ne 2 ]; then
  echo "FAIL: expected exactly two UCID-* folders (one pre-existing + one new), got ${#PRODUCED[@]}"
  ls -1 "$SAVE_DIR"
  exit 1
fi

# Find the NEW one (not the pre-seeded UCID-0099).
NEW=""
for d in "${PRODUCED[@]}"; do
  base=$(basename "$d")
  if [[ "$base" != UCID-0099* ]]; then
    NEW="$base"
  fi
done

if [ -z "$NEW" ]; then
  echo "FAIL: could not identify the new folder"
  exit 1
fi

echo "produced: $NEW"

# 5. Assert: starts with UCID-0100 (max+1 from the pre-seeded 0099).
if [[ "$NEW" != UCID-0100\ * ]]; then
  echo "FAIL: expected UCID-0100, got '$NEW'"
  exit 1
fi

# 6. Assert: no forbidden chars (parens, ampersand, exclam, smart quotes).
if echo "$NEW" | grep -qE '[()&!#?]|['\'']|[“”‘’]'; then
  echo "FAIL: forbidden char found in folder name: $NEW"
  exit 1
fi

# 7. Assert: frames/ subdir exists with extracted JPEGs inside the new folder.
#    (download/ is only created for URL sources; local-file runs skip it.)
NEW_PATH="$SAVE_DIR/$NEW"
if [ ! -d "$NEW_PATH/frames" ]; then
  echo "FAIL: frames/ missing under $NEW_PATH"
  ls -1 "$NEW_PATH"
  exit 1
fi
if ! ls "$NEW_PATH"/frames/frame_*.jpg >/dev/null 2>&1; then
  echo "FAIL: no frames extracted under $NEW_PATH/frames/"
  exit 1
fi

# 8. Assert: report stdout points at the FINAL folder, not a staging tmp.
if ! grep -q "$NEW_PATH" "$TMP/watch.stdout"; then
  echo "FAIL: report stdout does not mention the final save-dir path"
  echo "--- stdout ---"; cat "$TMP/watch.stdout"
  exit 1
fi
if grep -q "watch-staging-" "$TMP/watch.stdout"; then
  echo "FAIL: report stdout still references a staging tmp dir"
  echo "--- stdout ---"; cat "$TMP/watch.stdout"
  exit 1
fi

echo "OK — UCID allocation, sanitisation, and path rewiring all pass."
