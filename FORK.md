# Fork notes

This fork of [kevinpardo/world-of-codecraft](https://github.com/kevinpardo/world-of-codecraft) trades the living village for a cheaper one. The village is a still showcase of districts. While the focused hero works, a dungeon replaces the village.

## Decisions

- **Why the fork exists:** the upstream village kept the Herdr window at about 33% of one CPU core. Every native `.loop()` animation redraws the whole strip each frame, and walkers, smoke and glows add more loops.
- **Static village:** the village draws no `.loop()` and runs no frame timer. Heroes are still sprites, markers (`!`, `?`, selection ring) are still, and night glows are static.
- **No NPCs:** walkers, animals, birds, fish and chimney smoke are removed with their art (`ambiance.js` and 11 creature folders).
- **No guards:** shell terminals no longer appear as warriors. Only agents are heroes.
- **Buildings by district:** each district (space, in `spaces()` order) owns one building: tower, forge, temple, barn, barracks, market. A seventh district shares the tower again. All heroes of a district stand at its building, whatever their class or status. A banner shows the district name above the heroes.
- **Dungeon trigger:** the dungeon shows automatically while the focused agent works. It is not a click or a key. Immersion mode keeps the village.
- **Dungeon animation:** one `cx.timer.every` at up to 6 fps steps every sprite and effect. It calls `notify` only when a visible frame changes. The dungeon uses no `.loop()`.
- **Scenes follow the activity hook:**
  - thinking: a "…" bubble;
  - reading: a tome at the shelf;
  - editing and commands: a creature fight;
  - tests: a dummy;
  - compacting: orbiting runes;
  - commit: a seal;
  - push: a pigeon;
  - repeated failures: a troll.
- **Heroes face right in the dungeon:** gpui-kit cannot flip images at run time, so `tools/mirror_heroes.py` pre-renders mirrored frames (`NN-g.png`) for idle, work and rest.
- **Subagents are allies:** each running subagent appears as a semi-transparent hero, up to 4, to the left of the main hero. Class follows the subagent type:
  - Explore, search, fetch and guide agents: ranger;
  - implementer: artificer;
  - Plan: priest;
  - everything else: warrior.

  While allies are present, the room switches to its summoning version.
- **Health is context used against fixed limits:** the bar is full at 0 context tokens and empty at `HEALTH_MAX = 250_000`. It turns yellow from `HEALTH_YELLOW = 150_000` and red from `HEALTH_RED = 200_000` (all in `kit.js`). Tokens, not percentages, because the window is 1M and percentages from different tools disagree. A status-line wrapper writes the count, because hooks do not receive context usage.
- **Dungeon art is procedural:** `tools/village-art/dungeon.py` models the room in voxels and renders it through the village engine, so it matches the village style without hand painting.
- **Fork, not a copy in dotfiles:** the mod is about 50 MB of PNGs, and the fork can still merge upstream.

## Current state

**CPU of the Herdr window,** sampled with `top` for 10 s on a quiet machine:

| View | CPU |
|---|---|
| Upstream village | ~33% |
| Static village | ~0.6% |
| Dungeon, thinking | ~8.6% |
| Dungeon, fight | ~9.0% |
| Dungeon, "Animations" off | ~1.7% |

**Files:**
- `mods/world-of-codecraft/place.js`: village, district buildings, banners, dungeon switch.
- `mods/world-of-codecraft/donjon.js`: dungeon view, scenes, effects, allies, HUD.
- `mods/world-of-codecraft/activite.js`: polls activity files, scene choice, blows, context used.
- `mods/world-of-codecraft/kit.js`: `healthBar`, `HEALTH_MAX`, `HEALTH_YELLOW`, `HEALTH_RED`.
- `mods/world-of-codecraft/art/donjon/`: `salle.png`, `salle-invocation.png` and `meta.json` (anchors in 1600×400 logical px).
- `tools/village-art/dungeon.py`: renders the room. It takes about 60–70 s on 10 cores.
- `tools/mirror_heroes.py`: writes the right-facing frames. Run it again after `tools/sync_heroes.py`.

**Data the mod reads,** from `~/.local/state/world-of-codecraft/`:
- `<terminal>.json`: activity, written by `integrations/claude-code/wocc-activity.py`. It now also records `allies: [{id, type}]`.
- `<terminal>-ctx.json`: `{"used", "size", "t"}` (context tokens in use, window size), written by a status-line wrapper. The wrapper lives in the owner's dotfiles (`claude/hooks/wocc-statusline.py`), not in this repo.

## Update and rebuild

1. Run `tools/install.sh` to copy the mod into `~/.config/herdr-app`.
2. Run `tools/village-art/.venv/bin/python tools/village-art/dungeon.py` to re-render the room.
3. Run `tools/village-art/.venv/bin/python tools/mirror_heroes.py` after hero frames change.
4. Merge `upstream/main` to take upstream changes. Expect conflicts in `place.js` and `activite.js`.

## Open items

- Allies stand close together and touch the hero at 1.25× scale. Spread them further left or draw them smaller.
- Only the tower banner has been checked on screen. The banner positions for the other buildings are estimates.
- Immersion mode has not been tested since the changes.
- The standalone `commande` block (immersion layout) shows no health bar.
- `art/ic-parchemin.svg` and the i18n keys `village`, `accountNone` and `campfire` are unused but still in the tree.
- `creatures-data.js` has no entry for the restored pigeon frames. Their sizes are a constant in `donjon.js`.
