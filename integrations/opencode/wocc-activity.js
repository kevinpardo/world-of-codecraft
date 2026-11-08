// World of Codecraft (Herdr layout): what this OpenCode agent is doing, for the village.
// Same file and fields as the Claude Code hook integrations/claude-code/wocc-activity.py:
// ~/.local/state/world-of-codecraft/<HC_TERMINAL_ID>.json, read by ~/.config/herdr-app/mods/world-of-codecraft/activite.js.
// OpenCode is a ranger (barn and fields): its creatures come from that district (wolf, boar).
// Outside Herdr (no HC_TERMINAL_ID) it does nothing. Child sessions' tools are ignored.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const READ = new Set(["read", "grep", "glob", "list", "lsp", "codesearch"]);
const EDIT = new Set(["edit", "write", "patch", "multiedit"]);
const WEB = new Set(["webfetch", "websearch"]);
const TEST = /(^|[\s;&|(])((bun|npm|pnpm|yarn|npx|bunx)\s+(run\s+)?test|vitest|jest|pytest|playwright\s+test|cargo\s+test|go\s+test|rspec|phpunit|mix\s+test|deno\s+test)\b/;
const COMMIT = /\bgit\s+(-C\s+\S+\s+)?commit\b/;
const PUSH = /\bgit\s+(-C\s+\S+\s+)?push\b/;

export const WoccActivityPlugin = async () => {
  const term = process.env.HC_TERMINAL_ID;
  if (!term) return {};
  const dir = path.join(os.homedir(), ".local", "state", "world-of-codecraft");
  const file = path.join(dir, `${term}.json`);
  const children = new Set(); // child session ids (subagents)
  const commands = new Map(); // callID -> bash command (to read it back after the call)

  const update = (fn) => {
    try {
      fs.mkdirSync(dir, { recursive: true });
      let s = {};
      try { s = JSON.parse(fs.readFileSync(file, "utf8")); } catch {}
      s.tache ??= 0;
      s.subs ??= 0;
      const now = Date.now();
      const act = (a) => { if (s.act !== a) { s.act = a; s.depuis = now; } };
      fn(s, act, now);
      s.t = now;
      fs.writeFileSync(`${file}.tmp`, JSON.stringify(s));
      fs.renameSync(`${file}.tmp`, file);
    } catch {}
  };
  const kind = (tool, cmd) =>
    EDIT.has(tool) ? "code" : READ.has(tool) ? "eclaire" : tool === "bash" ? (TEST.test(cmd) ? "test" : "commande") : WEB.has(tool) ? "web" : null;

  return {
    "chat.message": async ({ sessionID }) => {
      if (sessionID && children.has(sessionID)) return;
      update((s, act) => { s.tache += 1; s.coups = 0; s.err = 0; s.errTache = 0; act("pense"); });
    },
    "tool.execute.before": async (input, output) => {
      if (input?.sessionID && children.has(input.sessionID)) return;
      const tool = String(input?.tool ?? "");
      const cmd = tool === "bash" ? String(output?.args?.command ?? "") : "";
      if (cmd) commands.set(input.callID, cmd);
      update((s, act) => {
        const k = kind(tool, cmd);
        if (k) act(k);
        if (tool === "task") s.subs += 1;
        s.outil = tool;
      });
    },
    "tool.execute.after": async (input, output) => {
      if (input?.sessionID && children.has(input.sessionID)) return;
      const tool = String(input?.tool ?? "");
      const cmd = commands.get(input?.callID) ?? "";
      commands.delete(input?.callID);
      const md = output?.metadata ?? {};
      const failed = Boolean(md.error) || (typeof md.exit === "number" && md.exit !== 0);
      update((s, act, now) => {
        if (tool === "task") s.subs = Math.max(0, s.subs - 1);
        if (failed) {
          s.err = (s.err ?? 0) + 1; s.errTache = (s.errTache ?? 0) + 1; s.errT = now;
          if (TEST.test(cmd)) s.essai = { ok: false, t: now };
          return;
        }
        if (EDIT.has(tool)) s.coups = (s.coups ?? 0) + 1;
        s.err = 0;
        if (TEST.test(cmd)) s.essai = { ok: true, t: now };
        if (COMMIT.test(cmd)) s.commitT = now;
        if (PUSH.test(cmd)) s.pushT = now;
      });
    },
    event: async ({ event }) => {
      const p = event?.properties ?? {};
      if (p.info?.id && p.info.parentID) children.add(p.info.id);
      const sid = p.sessionID ?? p.info?.id;
      if (sid && children.has(sid)) return;
      if (event?.type === "session.compacted") update((s, act) => act("medite"));
      else if (event?.type === "session.idle") update((s, act) => { s.subs = 0; act("fini"); });
      else if (event?.type === "session.deleted") { try { fs.unlinkSync(file); } catch {} }
    },
  };
};

export default {
  id: "world-of-codecraft.activity",
  server: WoccActivityPlugin,
  setup() {},
};
