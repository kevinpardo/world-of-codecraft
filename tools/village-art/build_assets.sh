#!/bin/sh
# Render the direction A sprites (buildings, props, trees, ground tiles) into tools/village-art/assets/.
# A few seconds per model. Needs numpy, scipy, pillow:
#   uv venv tools/village-art/.venv && uv pip install --python tools/village-art/.venv/bin/python numpy scipy pillow
set -eu
cd "$(dirname "$0")"
PY=${PY:-.venv/bin/python}
mkdir -p assets
for n in tavern townhall magetower forge barracks temple barn stall-red stall-blue stall-green well noticeboard campfire \
         tree-oak tree-pine bush tree-autumn rocks fence-x fence-y; do
  OUT=assets/p-$n "$PY" buildings.py "$n" >/dev/null &
done
wait
"$PY" extras.py >/dev/null
"$PY" - <<'PYEOF'
import glob, json, os, shutil
meta = json.load(open("assets/meta.json")) if os.path.exists("assets/meta.json") else {}
for d in sorted(glob.glob("assets/p-*")):
    for f in glob.glob(d + "/*.png"):
        shutil.copy(f, "assets/")
    meta.update(json.load(open(d + "/meta.json")))
    shutil.rmtree(d)
json.dump(meta, open("assets/meta.json", "w"), indent=1)
print(len(meta), "sprites in assets/")
PYEOF
