#!/usr/bin/env python3
"""World of Codecraft (Herdr layout): what each Claude Code agent is doing, for the village.

Claude Code hook (async, never blocks). Writes ~/.local/state/world-of-codecraft/<HC_TERMINAL_ID>.json, read by
~/.config/herdr-app/mods/world-of-codecraft/activite.js to pick the hero's scene while Herdr says "working".

  act      pense (thinking) | eclaire (reading/searching) | code (editing) | commande (bash)
           | test (running tests) | web (web search/fetch) | medite (compacting) | fini (turn over)
  outil    last tool name          t      last event (ms)       depuis  when act started (ms)
  coups    successful edits and commands this task (each one = a blow on the creature)
  err      consecutive tool failures, errT the last one (ms)
  subs     running subagents       tache  prompt counter (seeds the creature drawn for the task)
  errTache tool failures this task (3+ = the next creature is a boss)
  essai    last test run {ok, t} (act "test" while it runs)   commitT / pushT  last git commit / push (ms)

Outside Herdr (no HC_TERMINAL_ID) it does nothing. Subagents' own tool calls are ignored.
"""
import fcntl, json, os, re, sys, time

term = os.environ.get("HC_TERMINAL_ID")
if not term:
    sys.exit(0)
try:
    ev = json.load(sys.stdin)
except Exception:
    sys.exit(0)
# tell Claude Code not to wait for us (async hook response), then do the work
print('{"async": true}', flush=True)

DIR = os.path.expanduser("~/.local/state/world-of-codecraft")
os.makedirs(DIR, exist_ok=True)
path = os.path.join(DIR, f"{term}.json")
name = ev.get("hook_event_name", "")
tool = ev.get("tool_name") or ""
sub = bool(ev.get("agent_id"))
now = int(time.time() * 1000)
cmd = str((ev.get("tool_input") or {}).get("command") or "") if tool == "Bash" else ""
# drop heredoc bodies and quoted strings: only the commands themselves count
cmd = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\s*\1\b", " ", cmd, flags=re.S)
cmd = re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", "''", cmd)
# only real commands: at the start of the command line or after ; & | ( (not inside quoted text or heredocs)
AT = r"(?:^|[;&|(]\s*)(?:\w+=\S+\s+)*"
TEST = re.compile(AT + r"((bun|npm|pnpm|yarn|npx|bunx)\s+(run\s+)?test|vitest|jest|pytest|playwright\s+test|cargo\s+test|go\s+test|rspec|phpunit|mix\s+test|deno\s+test)\b", re.M)
COMMIT = re.compile(AT + r"git\s+(-C\s+\S+\s+)?commit\b", re.M)
PUSH = re.compile(AT + r"git\s+(-C\s+\S+\s+)?push\b", re.M)

READ = {"Read", "Grep", "Glob", "LS", "NotebookRead", "LSP", "ToolSearch"}
EDIT = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
WEB = {"WebSearch", "WebFetch"}


def kind(t):
    if t in EDIT:
        return "code"
    if t in READ:
        return "eclaire"
    if t == "Bash":
        return "test" if TEST.search(cmd) else "commande"
    if t in WEB or (t.startswith("mcp__") and any(k in t for k in ("search", "fetch", "scrape", "exa", "firecrawl", "context7", "docs"))):
        return "web"
    return None  # Agent, TodoWrite, Skill, AskUserQuestion...: keep the current scene


if name == "SessionEnd":
    try:
        os.remove(path)
    except OSError:
        pass
    sys.exit(0)

with open(os.path.join(DIR, ".lock"), "w") as lk:
    fcntl.flock(lk, fcntl.LOCK_EX)
    try:
        with open(path) as f:
            s = json.load(f)
    except Exception:
        s = {}
    s.setdefault("tache", 0)
    s.setdefault("subs", 0)

    def act(a):
        if s.get("act") != a:
            s["act"], s["depuis"] = a, now

    if name in ("SubagentStart",):
        s["subs"] = s["subs"] + 1
    elif name == "SubagentStop":
        s["subs"] = max(0, s["subs"] - 1)
    elif sub:
        pass  # a subagent's own tools: the main hero's scene stays
    elif name == "UserPromptSubmit":
        s.update(tache=s["tache"] + 1, coups=0, err=0, errTache=0)
        act("pense")
    elif name == "PreToolUse":
        k = kind(tool)
        if k:
            act(k)
        s["outil"] = tool
    elif name == "PostToolUse":
        if tool in EDIT or tool == "Bash":  # every successful edit or command is a blow on the creature
            s["coups"] = s.get("coups", 0) + 1
        s["err"] = 0
        if TEST.search(cmd):
            s["essai"] = {"ok": True, "t": now}
        if COMMIT.search(cmd):
            s["commitT"] = now
        if PUSH.search(cmd):
            s["pushT"] = now
    elif name == "PostToolUseFailure":
        s["err"] = s.get("err", 0) + 1
        s["errTache"] = s.get("errTache", 0) + 1
        s["errT"] = now
        if TEST.search(cmd):
            s["essai"] = {"ok": False, "t": now}
    elif name == "PreCompact":
        act("medite")
    elif name == "SessionStart":
        if ev.get("source") == "compact":
            act("pense")
        else:
            s.update(subs=0, err=0, coups=0)
            act("fini")
    elif name == "Stop":
        s["subs"] = 0
        act("fini")
    s["t"] = now
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(s, f)
    os.replace(tmp, path)
