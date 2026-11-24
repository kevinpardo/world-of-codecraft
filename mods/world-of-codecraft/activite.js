// What each hero is doing while Herdr says "working", from the Claude Code hook
// (integrations/claude-code/wocc-activity.py and integrations/opencode/wocc-activity.js in the repo
// → ~/.local/state/world-of-codecraft/<terminal>.json), and the scenes it plays:
//   pense    thinking            idle pose + "…" bubble
//   eclaire  reading, searching  stands at the bookshelf
//   combat   editing code        fights a creature drawn for the task (imp, wolf, goblin); every successful
//                                edit is a blow, 4 blows fell it and the next one comes; a failed tool = the
//                                hero is hit (red flash, recoil, "Ouch!")
//   medite   compacting          sits cross-legged (`rest`)
//   test     running tests       strikes a training dummy; passed = the dummy falls + "Tests passed!",
//                                failed = "Tests failing" (the result stays 5 s, whatever the scene)
//   travail  bash and the rest   the usual `work` loop
// plus, whatever the scene: a "Sealed!" bubble on a git commit and a "Sent" one on a git push.
// Lot 2: six creatures in the draw (imp, wolf, goblin, boar, rust golem, spectre); a task with 3+ failed
// tools brings the forest troll, a boss of 8 blows.
// Anti-zapping: a scene changes only when the new one has been asked for 8 s and the current one has
// lasted 15 s; 20 s / 40 s when it means going to or from the bookshelf (meditation, tests and the
// end of work switch at once).

import { home, readTextFile } from "herdr";
import { hash, heroOf } from "./kit.js";

const POLL = 1000;
const STABLE = 8000; // the new scene must be asked for this long
const HOLD = 15000; // and the current one must have lasted this long
const STABLE_WALK = 20000; // a scene that makes the hero walk (to or from the forest edge) is stickier:
const HOLD_WALK = 40000; // otherwise read / run / read loops send it back and forth
const FRESH = 15 * 60_000; // an activity file older than this is ignored
const BLOWS = 4; // successful edits to fell a creature
const BOSS_BLOWS = 8; // the troll's
const BOSS_AFTER = 3; // failed tools in a task before the troll comes
const SPECIES = ["diablotin", "loup", "gobelin", "sanglier", "golem", "spectre"];
/** Each district's own beasts. Mages (Claude Code) draw from the whole pool; the others (OpenCode = ranger
 *  at the barn, via integrations/opencode/wocc-activity.js) from their district's. */
export const DISTRICT = { atelier: ["golem", "gobelin"], grange: ["loup", "sanglier"], temple: ["spectre"], etal1: ["gobelin", "loup"] };
const HOME = { artificier: "atelier", rodeur: "grange", pretre: "temple", voleur: "etal1" };
export const clsOf = (a) => (a.demoHero ? { mage: "mage", artificer: "artificier", ranger: "rodeur", priest: "pretre", rogue: "voleur", warrior: "guerrier" }[a.demoHero.split("-")[1]] : heroOf(a.address, a.program).cls);
export const RESULT = 5000; // a test result stays on screen this long
const SCENE_OF = { pense: "pense", eclaire: "eclaire", web: "eclaire", code: "combat", commande: "combat", medite: "medite", test: "test" };
export const boss = (s) => (s?.errTache ?? 0) >= BOSS_AFTER;
export const blowsFor = (s) => (boss(s) ? BOSS_BLOWS : BLOWS);
export const recent = (t, ms) => Boolean(t) && Date.now() - t < ms;

/** The scene the activity file asks for (null = the plain status behaviour). */
function wanted(a, s, now) {
  if (a.status !== "working" || !s || now - (s.t ?? 0) > FRESH) return null;
  return SCENE_OF[s.act] ?? null;
}

export class Activites {
  constructor() {
    this.files = new Map(); // address -> parsed activity file
    this.scenes = new Map(); // address -> { scene, since, cand, candSince }
    this.hits = new Map(); // address -> { coups, at, felled: [{ species, at }] }
    this.timer = null;
    this.busy = false;
    this.ctxs = new Map(); // address -> { used, t }: context tokens in use, from the status-line wrapper
    this.ctxAddr = null;
    this.ctxTimer = null;
  }

  /** Context tokens an agent has in use, or null (no file, or older than FRESH). */
  ctxUsed(addr) {
    const c = this.ctxs.get(addr);
    return c && Date.now() - (c.t ?? 0) < FRESH ? c.used : null;
  }

  /** Reads the selected agent's context file now and every 10 s; redraws only when the shown value changes. */
  watchCtx(cx, addr) {
    if (addr === this.ctxAddr) return;
    this.ctxAddr = addr;
    if (this.ctxTimer) { this.ctxTimer.cancel(); this.ctxTimer = null; }
    if (!addr) return;
    const read = async (acx) => {
      let c = null;
      try { c = JSON.parse((await readTextFile(`${home()}/.local/state/world-of-codecraft/${addr}-ctx.json`)) ?? "null"); } catch { c = null; }
      const before = this.ctxUsed(addr);
      if (c && typeof c.used === "number") this.ctxs.set(addr, c); else this.ctxs.delete(addr);
      if (this.ctxUsed(addr) !== before) acx.notify();
    };
    cx.spawn(read);
    this.ctxTimer = cx.timer.every(10_000, read);
  }

  /** The scene a unit plays now (decided in the poll, read in render). */
  scene(addr) {
    if (this.off) return null;
    return this.scenes.get(addr)?.scene ?? null;
  }

  file(addr) {
    return this.files.get(addr) ?? null;
  }

  /** Polls the activity files while some agent works; notifies only when something visible changes. */
  watch(cx, list, hidden, off = false) {
    this.list = list;
    this.off = off;
    const need = !hidden && !off && list.some((a) => a.status === "working" || this.scenes.has(a.address));
    if (need && !this.timer) this.timer = cx.timer.every(POLL, (cx) => this.poll(cx));
    else if (!need && this.timer) { this.timer.cancel(); this.timer = null; }
  }

  async poll(cx) {
    if (this.busy) return;
    this.busy = true;
    let changed = false;
    try {
      const now = Date.now();
      const dir = `${home()}/.local/state/world-of-codecraft`;
      for (const a of this.list ?? []) {
        if (a.demoAct) { changed = this.apply(a, a.demoAct, now) || changed; continue; }
        if (a.status !== "working") { changed = this.apply(a, null, now) || changed; continue; }
        let s = null;
        try { s = JSON.parse((await readTextFile(`${dir}/${a.address}.json`)) ?? "null"); } catch { s = null; }
        const old = this.files.get(a.address);
        if (JSON.stringify(old) !== JSON.stringify(s)) { this.files.set(a.address, s); changed = true; }
        changed = this.apply(a, s, now) || changed;
      }
      // short-lived flashes (blow on the creature, hero hit): redraw when they start or end
      for (const a of this.list ?? []) {
        const h = this.hits.get(a.address), s = this.files.get(a.address) ?? a.demoAct;
        const flash = `${h && now - h.at < 900}:${Boolean(s?.errT && s.err > 0 && now - s.errT < 1500)}:${recent(s?.essai?.t, RESULT)}:${recent(s?.commitT, 4000)}:${recent(s?.pushT, 7000)}`;
        if (h && h.flash !== flash) { h.flash = flash; changed = true; }
      }
      const alive = new Set((this.list ?? []).map((a) => a.address));
      for (const k of [...this.scenes.keys()]) if (!alive.has(k)) { this.scenes.delete(k); changed = true; }
      // a felled creature's puff lasts 1.2 s
      for (const h of this.hits.values()) {
        const n = h.felled.length;
        h.felled = h.felled.filter((f) => now - f.at < 1200);
        if (h.felled.length !== n) changed = true;
      }
    } finally { this.busy = false; }
    if (changed) cx.notify();
  }

  /** Anti-zapping decision for one unit; true when its scene changed. */
  apply(a, s, now) {
    const want = wanted(a, s, now);
    if (s) this.blows(a.address, s, now, clsOf(a));
    let st = this.scenes.get(a.address);
    if (!st) {
      if (!want) return false;
      this.scenes.set(a.address, { scene: want, since: now, cand: want, candSince: now });
      return true;
    }
    if (want === st.scene) { st.cand = want; st.candSince = now; return false; }
    if (st.cand !== want) { st.cand = want; st.candSince = now; }
    const at_once = want === "medite" || want === "test" || want === null || st.scene === "medite";
    const walk = want === "eclaire" || st.scene === "eclaire";
    if (at_once || (now - st.candSince >= (walk ? STABLE_WALK : STABLE) && now - st.since >= (walk ? HOLD_WALK : HOLD))) {
      if (!want) this.scenes.delete(a.address);
      else { st.scene = want; st.since = now; }
      return true;
    }
    return false;
  }

  /** Tracks blows (successful edits) to fell creatures. */
  blows(addr, s, now, cls) {
    let h = this.hits.get(addr);
    const coups = s.coups ?? 0;
    if (!h || coups < h.coups || h.tache !== s.tache) { h = { coups, at: 0, felled: [], tache: s.tache }; this.hits.set(addr, h); return; }
    if (coups > h.coups) {
      const B = blowsFor(s);
      const before = Math.floor(h.coups / B), after = Math.floor(coups / B);
      if (after > before) h.felled.push({ species: boss(s) ? "troll" : species(addr, s.tache, before, cls), at: now });
      h.coups = coups;
      h.at = now;
    }
  }
}

/** The creature for a task: drawn from the task number and the hero, one per BLOWS edits. */
export function species(addr, tache, n, cls = "mage") {
  const pool = (cls !== "mage" && DISTRICT[HOME[cls]]) || SPECIES;
  return pool[hash(`${addr}:${tache}:${n}`) % pool.length];
}
