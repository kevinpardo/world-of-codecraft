#!/bin/sh
# Install (or update) World of Codecraft into the Herdr app's home.
#
#   tools/install.sh                 copy the layout, its theme and its mod
#   tools/install.sh --integrations  also link the activity hook (Claude Code) and plugin (OpenCode)
#   tools/install.sh --quiet         no output (used by the repo's local Claude Code hook)
#
# The repo is the only source: the copy in the Herdr home is real files (Herdr loads images and
# hot-reloads mods only from real paths inside its home, not through symlinks), refreshed by this
# script. Don't edit the installed copy; edit the repo and run this again.
# HERDR_APP_HOME picks another Herdr home (default ~/.config/herdr-app).
set -eu

REPO=$(cd "$(dirname "$0")/.." && pwd)
DEST=${HERDR_APP_HOME:-"$HOME/.config/herdr-app"}
QUIET=0
INTEGRATIONS=0
for a in "$@"; do
  case "$a" in
    --quiet) QUIET=1 ;;
    --integrations) INTEGRATIONS=1 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done
say() { [ "$QUIET" = 1 ] || echo "$@"; }

[ -d "$DEST" ] || { echo "Herdr home not found: $DEST (start the Herdr app once first)" >&2; exit 1; }
mkdir -p "$DEST/mods" "$DEST/layouts" "$DEST/themes"

# the mod: an exact copy (rsync only rewrites what changed, so Herdr reloads once)
[ -L "$DEST/mods/world-of-codecraft" ] && rm -f "$DEST/mods/world-of-codecraft"
rsync -a --delete --exclude '.DS_Store' "$REPO/mods/world-of-codecraft/" "$DEST/mods/world-of-codecraft/"
for f in layouts/World-of-Codecraft.json layouts/World-of-Codecraft.png themes/World-of-Codecraft.json; do
  [ -L "$DEST/$f" ] && rm -f "$DEST/$f" # a symlink left by an older setup
  rsync -a "$REPO/$f" "$DEST/$f"
done
# the immersive mode used to be a second layout: now it is a mode of this one
rm -f "$DEST/layouts/World-of-Codecraft-Immersion.json" "$DEST/layouts/World-of-Codecraft-Immersion.png" "$DEST/layouts/.state/World-of-Codecraft-Immersion.json"
say "World of Codecraft installed in $DEST"

if [ "$INTEGRATIONS" = 1 ]; then
  # Claude Code: link the hook, then register it in ~/.claude/settings.json (see README)
  mkdir -p "$HOME/.claude/hooks"
  ln -sfn "$REPO/integrations/claude-code/wocc-activity.py" "$HOME/.claude/hooks/wocc-activity.py"
  say "Claude Code hook linked: ~/.claude/hooks/wocc-activity.py (register it in settings.json, see README)"
  # OpenCode: plugins in ~/.config/opencode/plugins load by themselves
  if [ -d "$HOME/.config/opencode" ]; then
    mkdir -p "$HOME/.config/opencode/plugins"
    ln -sfn "$REPO/integrations/opencode/wocc-activity.js" "$HOME/.config/opencode/plugins/wocc-activity.js"
    say "OpenCode plugin linked: ~/.config/opencode/plugins/wocc-activity.js"
  fi
fi
