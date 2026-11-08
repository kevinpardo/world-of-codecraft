# Direction A: pixel art HD

**The look:** chunky, warm high-fantasy pixel art at twice today's density. One art pixel is one logical pixel, shown at 2× on Retina. Buildings are 150 to 290 px tall and have oversized roofs, curved spires and gold trims. Heroes are 45 to 60 px tall, with big heads and readable faces. Every surface has a texture: shingles, stone courses, half-timbering, planks, moss.

**References (in words):** modern premium iso pixel-art city builders and cozy RPGs. Uses hue-shifted ramps (Slynyrd/Saint11 school), selective outlines and voxel-to-pixel pipelines (rendered 3D, then quantised by hand-made rules). The proportions follow the stylised high-fantasy MMO look. Nothing is copied.

**Method:** every asset is code (Python, numpy and scipy, see `engine.py`):
- Each asset is a voxel model: buildings use 1 unit voxels, heroes 0.5 unit voxels.
- The renderer traces one ray per pixel, then:
  - quantises lighting onto a 7-step ramp per material;
  - adds a procedural texture per material;
  - casts shadows and adds ambient occlusion;
  - adds a rim light on top-left edges;
  - draws a 1 px coloured outline.
- Outputs per asset: colour, ground shadow and night emissive layer, all at 2×. `meta.json` holds the anchors.

## Rules
- **Projection:** 2:1 dimetric, `u = x − y`, `v = (x + y)/2 − z`. A tile is 32×32 world units, or 64×32 logical px (128×64 at 2×). The angle is the same for every asset because every asset goes through the same renderer.
- **Light:** comes from the top-left, `L = (−0.30, 0.42, 0.86)`. Roofs and tops are brightest. Left walls (+y) are mid-lit. Right walls (+x) are in shadow, with a little bounce light. Cast shadows fall to the right on a separate layer, colour `#181234` at about 40 % in 4 steps.
- **Ramps:** every material has 7 steps generated from one base colour. Darks drift toward blue-violet (232°) and saturate. Lights drift toward yellow (48°) and desaturate.
- **Dithering:** only a 4×4 Bayer pattern at ramp boundaries. Amplitude is 0.45 of a step on buildings and 0.12 on heroes.
- **Outline:** 1 px, outside the silhouette. The colour is the material's darkest step, darkened and pushed toward purple. Inner depth breaks get the darkest step of the surface behind. Emissive parts keep coloured outlines.
- **Base palette:**

| Material | Hex |
|---|---|
| Stone | `#9a8f86` |
| Dark stone | `#6f6875` |
| Plaster | `#e8d6b0` |
| Timber | `#6b3f26` |
| Red roof | `#c4482f` |
| Blue roof | `#3f6aa8` |
| Violet roof | `#6b3fb0` |
| Slate | `#4a4f63` |
| Barn red | `#a33a2a` |
| Gold | `#e0a32a` |
| Marble | `#e9e2d6` |
| Leaf | `#4f8f34` |
| Pine | `#2f6a45` |
| Grass | `#5f9a3a` |
| Dirt | `#9a7650` |
| Water | `#2f80b4` |

  Glow colours: fire `#ffa12b`, arcane `#a86bff`, holy `#ffd45e`, windows at night `#ffcf6a`.

## Night and glow
- Emissive materials (fire, arcane, holy light, window glass) are written to a `-night.png` layer.
- At night the whole scene is graded to `rgb·(0.20, 0.25, 0.46)` plus a blue lift.
- The emissive layer is then pasted at full brightness, with a two-radius bloom posterised into pixel-art steps and dithered.
- This lights the ground around windows, fires and magic. Cast shadows drop to 45 % at night.

## States
| State | How it reads |
|---|---|
| working | Work pose (raised tool, drawn bow, cast orb), class effects (arcane sparkles, forge sparks) |
| blocked `!` | Yellow `!` (2-px glyph pixels, gold outline, glow) above the head, flashing yellow iso ring, parchment bubble « À l'aide ! » |
| done `?` | Gold `?`, golden halo ring, golden star sparkles |
| idle | Sitting pose on a stump with a mug, round the campfire, rising `z` |
| selected | Green iso ring with ticks |

Markers, rings and bubbles stay lit at night.

## Files
- `engine.py`: renderer.
- `tex.py`: palette and textures.
- `kit3d.py`: windows, doors, timber frames, banners and other parts.
- `buildings.py`, `heroes.py` (race × class × pose), `extras.py` (tiles, markers, icons, panel), `compose.py` (mock-ups), `sheet.py`.
- Re-run: `.venv/bin/python buildings.py && .venv/bin/python heroes.py && .venv/bin/python extras.py && .venv/bin/python compose.py && .venv/bin/python sheet.py`. It takes about 30 s.
