#!/usr/bin/env bash
# Rebuild missing assets, render all scenes, mix audio, burn subtitles, mux the final MP4.
#   ./render.sh                 full render
#   ./render.sh --scenes 03,05  re-render only those scene clips (others are reused from cache)
#   ./render.sh --preview 22.0  write a still frame at 22.0 s to output/build/stills
set -euo pipefail
cd "$(dirname "$0")"
python3 -m scripts.build_assets
python3 -m src.render "$@"
