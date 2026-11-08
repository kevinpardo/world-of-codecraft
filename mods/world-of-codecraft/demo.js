// Demo districts and heroes for screenshots (props.demo on a block): the board, the command panel and the
// header show these instead of the person's own spaces, tabs and agents. The village has its own demo
// heroes (place.js). Names are generic so a preview never shows anyone's projects.

const tab = (id, index, name, status, panes = 1, active = false) => ({ id, index, name, named: true, status, panes, active, settled: false });

export const DEMO_SPACES = [
  { id: "demo-ironhold", index: 1, name: "Ironhold", named: true, machine: null, active: false,
    tabs: [tab("demo-t1", 1, "Mend the bridge", "blocked"), tab("demo-t2", 2, "Survey the mines", "working")] },
  { id: "demo-elderwood", index: 2, name: "Elderwood", named: true, machine: null, active: false,
    tabs: [tab("demo-t3", 1, "Chart the realm", "done"), tab("demo-t4", 2, "Tame the archives", "idle")] },
  { id: "demo-valbrume", index: 3, name: "Valbrume", named: true, machine: null, active: true,
    tabs: [tab("demo-t5", 1, "Forge the realm", "working", 2, true), tab("demo-t6", 2, "Guard the gates", null)] },
];

const agent = (address, space, tabId, status, key, name) => ({ address, space, tab: tabId, status, program: { key, name, shell: false }, title: name, seq: 0 });

export const DEMO_AGENTS = [
  agent("demo-a1", "demo-ironhold", "demo-t1", "blocked", "claude", "Claude Code"),
  agent("demo-a2", "demo-ironhold", "demo-t2", "working", "codex", "Codex"),
  agent("demo-a3", "demo-elderwood", "demo-t3", "done", "opencode", "OpenCode"),
  agent("demo-a4", "demo-elderwood", "demo-t4", "idle", "gemini", "Gemini"),
  agent("demo-a5", "demo-valbrume", "demo-t5", "working", "claude", "Claude Code"),
  agent("demo-a6", "demo-valbrume", "demo-t5", "working", "codex", "Codex"),
];

/** The unit the command panel shows in a demo. */
export const DEMO_SELECTED = { ...DEMO_AGENTS[4], tab_name: "Forge the realm", space_name: "Valbrume" };

/** The chronicle shown in a demo (English; a demo is for screenshots). */
const m = (min) => Date.now() - min * 60_000;
export const DEMO_LOG = [
  { at: m(1), text: "[Mage Tower] Thrakk, Orc mage (Claude Code) sets out on a quest \"Forge the realm\"", kind: "working", address: null },
  { at: m(4), text: "[Barracks] Brann, Human warrior (Codex) needs help", kind: "blocked", address: null },
  { at: m(9), text: "[Barn and fields] Liriel, Elf ranger (OpenCode) has finished the quest \"Chart the realm\"", kind: "done", address: null },
  { at: m(15), text: "[Campfire] Gromdal, Dwarf artificer (Gemini) rests by the campfire", kind: "idle", address: null },
];
