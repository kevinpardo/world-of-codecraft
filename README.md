# World of Codecraft

A high-fantasy layout for [Herdr](https://herdr.dev). Your coding agents become heroes
in Valbrume, a village drawn in isometric pixel art, built around one big terminal.

![World of Codecraft](preview.png)

- **Every agent is a hero.** Its class comes from the program it runs: Claude Code is a
  Mage at the tower, Codex an Artificer at the forge, Gemini a Priest at the temple,
  OpenCode a Ranger at the barn, and so on. Its race and name come from its terminal.
- **The village shows what each hero is doing.** A hero who needs you raises a flashing
  `!`. A hero who has finished shows a golden `?`. Idle heroes sit around the campfire.
- **With the optional activity integration, heroes act out the work itself.** A hero
  reading code scouts at the forest edge under circling ravens. Editing code or running
  commands, it fights a creature (imp, wolf, goblin, boar, rust golem, spectre), one blow per successful edit; a
  task full of failures brings a troll boss. Tests are a training dummy, a commit gets a wax
  seal, a push sends a carrier pigeon, compaction is meditation, and every subagent is a
  wisp.
- **The village lives on its own.** Villagers walk the road, hens peck by the barn, a cat
  naps at the tavern, fish leap in the river, a stag comes out at dawn, and a guard with a
  lantern walks the night.
- **An immersive mode** (header button or ctrl-shift-i) swaps the village and the terminal: the village fills
  the window at the same resolution, on a map three times taller with a forest to the north and fields and
  groves to the south, and you drag it to look around.
- **Spaces are districts and tabs are quests,** on the left, with heraldic banners.
- **Days and nights** follow your clock, with lit windows, a glowing forge and smoking
  chimneys.
- **French or English,** picked from your system language.
- **An « Animations » switch** under the minimap turns everything to still images when you
  want to save CPU.
- **A warm terminal theme**: dark oak background, parchment text and a gold cursor.

## Install

Ask your agent to add `herdr.dev/layouts/kevinpardo/world-of-codecraft`, or:

```sh
git clone https://github.com/kevinpardo/world-of-codecraft
cd world-of-codecraft
tools/install.sh                  # copies the layout, theme and mod into ~/.config/herdr-app
herdr-app do layout.switch '{"name":"World-of-Codecraft"}'
```

Then merge `mods/world-of-codecraft/KEYS.json` into your `keys.json`: `ctrl-shift-j`
toggles the village and `ctrl-shift-b` toggles the left column. Run `tools/install.sh`
again after a `git pull`. It installs real files, not symlinks: Herdr loads images and
reloads mods only from real files inside its home.

### Activity scenes (optional)

The scenes need each agent to say what it is doing. Two small integrations write that to
`~/.local/state/world-of-codecraft/<terminal>.json`:

```sh
tools/install.sh --integrations
```

- **OpenCode:** the plugin is linked into `~/.config/opencode/plugins/` and loads at the
  next start.
- **Claude Code:** the hook is linked to `~/.claude/hooks/wocc-activity.py`. Register it
  in `~/.claude/settings.json` for these events: `UserPromptSubmit`, `PreToolUse`,
  `PostToolUse`, `PostToolUseFailure`, `PreCompact`, `SubagentStart`, `SubagentStop`,
  `Stop`, `SessionStart`, `SessionEnd`. Each entry looks like this:

  ```json
  { "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/hooks/wocc-activity.py\" 2>/dev/null || true", "timeout": 5 }] }
  ```

  The hook answers `{"async": true}` at once, so it never slows Claude down, and does
  nothing outside Herdr.

## Language

The interface is in French when your system language is French, and in English otherwise.
To force one, start Herdr with `WOCC_LANG=fr` or `WOCC_LANG=en`.

## What it reads and runs

- The activity files above, if the integrations are installed.
- The Claude quota files of the author's two-account setup, cduo
  (`~/.local/state/claude-duo/quota-{A,B}.json`), only if they exist. They add the gold
  and wood gauges, the treasury and the fair; otherwise those stay hidden.
- Once per start, `sh` to read your system language.

The mod makes no network calls.

## Credits

Code and art by Kevin Pardo, MIT licensed. The heroes, creatures and villagers were made
with AI image generation, then cut, animated and graded by hand; the sources and the
scripts that rebuild the art are in `tools/`. The fonts are Cinzel, Alegreya Sans,
Jacquard 24 and Jersey 15, all under the SIL Open Font License.

World of Codecraft is an original work and a playful nod to the MMOs we grew up with.
It is not affiliated with or endorsed by any game publisher.
