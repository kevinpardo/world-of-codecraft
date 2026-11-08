// What each hero is doing while Herdr says "working", from the Claude Code hook
// (integrations/claude-code/wocc-activity.py and integrations/opencode/wocc-activity.js in the repo
// → ~/.local/state/world-of-codecraft/<terminal>.json), and the scenes it plays:
//   pense    thinking            idle pose + "…" bubble
//   eclaire  reading, searching  walks to the forest edge near its building, ravens circling
//   combat   editing code        fights a creature drawn for the task (imp, wolf, goblin); every successful
//                                edit is a blow, 4 blows fell it and the next one comes; a failed tool = the
//                                hero is hit (red flash, recoil, "Ouch!")
//   medite   compacting          sits cross-legged (`rest`), runes orbit and a crystal pulses
//   test     running tests       strikes a training dummy; passed = the dummy falls + "Tests passed!",
//                                failed = "Tests failing" (the result stays 5 s, whatever the scene)
//   travail  bash and the rest   the usual `work` loop
// plus, whatever the scene: familiars (one wisp per running subagent), a wax seal and "Sealed!" on a
// git commit, a carrier pigeon flying off east on a git push.
// Lot 2: six creatures in the draw (imp, wolf, goblin, boar, rust golem, spectre); a task with 3+ failed
// tools brings the forest troll, a boss of 8 blows.
// Anti-zapping: a scene changes only when the new one has been asked for 8 s and the current one has
// lasted 15 s; 20 s / 40 s when it means walking to or from the forest edge (meditation, tests and the
// end of work switch at once).

import { div, image } from "gpui-kit";
import { home, readTextFile } from "herdr";
import { hash, UI, C, heroOf } from "./kit.js";
import { CREATURES } from "./creatures-data.js";
import { t as tr } from "./i18n.js";

const ART = "mods/world-of-codecraft/art";
const CRE = `${ART}/creatures`;
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
const clsOf = (a) => (a.demoHero ? { mage: "mage", artificer: "artificier", ranger: "rodeur", priest: "pretre", rogue: "voleur", warrior: "guerrier" }[a.demoHero.split("-")[1]] : heroOf(a.address, a.program).cls);
const RESULT = 5000; // a test result stays on screen this long
const SCENE_OF = { pense: "pense", eclaire: "eclaire", web: "eclaire", code: "combat", commande: "travail", medite: "medite", test: "test" };
const boss = (s) => (s?.errTache ?? 0) >= BOSS_AFTER;
const blowsFor = (s) => (boss(s) ? BOSS_BLOWS : BLOWS);
const recent = (t, ms) => Boolean(t) && Date.now() - t < ms;

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
        if (a.guard || a.status !== "working") { changed = this.apply(a, null, now) || changed; continue; }
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

  /** The anim a scene plays (null = the status default). */
  anim(addr) {
    const sc = this.scene(addr);
    return sc === "pense" ? "idle" : sc === "eclaire" ? "idle" : sc === "medite" ? "rest" : sc ? "work" : null;
  }

  /** Extra layers hung from a unit's feet point, for its scene. `head` = top of the hero sprite. */
  layers(u, head, night, t) {
    const addr = u.a.address;
    const sc = this.scene(addr);
    const s = this.file(addr) ?? u.a.demoAct ?? null;
    const out = [];
    const sfx = night ? "-n" : "";
    if (sc === "pense") {
      out.push(div().absolute().left(14).top(head - 6).h(20).px(6).rounded(10).bg(C.parch).border_2().border_color(C.woodDark)
        .flex().items_center().font_family(UI).text_size(15).text_color(C.woodDark).whitespace_nowrap()
        .frames(["·", "· ·", "· · ·", "· · ·"], 420));
    }
    if (sc === "eclaire") {
      // two ravens circling above the scout (two flight frames crossfading = wing beats)
      for (let k = 0; k < 2; k++) {
        const per = 5200 + k * 1700, cx0 = -40 + k * 30, cy0 = head - 34 - k * 14;
        const R = CREATURES.corbeau;
        if (!R) break;
        const f0 = R.vol0, f2 = R.vol2;
        // a zero-size anchor (the bird's centre) moving on a loose ellipse; both frames centred on it
        out.push(div().absolute().left(cx0).top(cy0).w(0).h(0)
          .loop("left", { from: cx0 - 30, to: cx0 + 60, period: per })
          .loop("top", { from: cy0 - 8, to: cy0 + 8, period: per / 2.3 })
          .child(image(`${CRE}/corbeau/vol2${sfx}.png`).absolute().left(-f2.w / 2).top(-f2.h / 2).w(f2.w).h(f2.h).loop("opacity", { from: 7, to: -6, period: 260 + k * 40, easing: "linear" }))
          .child(image(`${CRE}/corbeau/vol0${sfx}.png`).absolute().left(-f0.w / 2).top(-f0.h / 2).w(f0.w).h(f0.h)
            .loop("opacity", { from: -6, to: 7, period: 260 + k * 40, easing: "linear" })));
      }
    }
    if (sc === "medite") {
      out.push(image(`${ART}/halo.svg`).absolute().left(-34).top(-46).w(68).h(40).opacity(0.7)
        .loop("opacity", { from: 0.25, to: 0.8, period: 2400 }));
      for (let k = 0; k < 3; k++) {
        const per = 3600, y0 = -40;
        out.push(image(`${ART}/etincelle.svg`).absolute().left(-30).top(y0).size(10)
          .loop("left", { from: -38 + k * 8, to: 30 - k * 8, period: per + k * 500 })
          .loop("top", { from: y0 - 18 + k * 6, to: y0 + 8 - k * 4, period: (per + k * 500) / 2 })
          .loop("opacity", { from: 0.3, to: 1, period: 900 + k * 200 }));
      }
      // the crystal: the condensed memory, pulsing above the head
      out.push(div().absolute().left(-4).top(head - 14).w(8).h(12).rounded(2).bg("#c9a7ff").border_1().border_color("#5b2ca8")
        .loop("top", { from: head - 12, to: head - 18, period: 1800 }).loop("opacity", { from: 0.55, to: 1, period: 1200 }));
    }
    // familiars: one wisp per running subagent (any scene)
    const subs = Math.min(4, s?.subs ?? 0);
    for (let k = 0; k < subs; k++) {
      const per = 4200 + k * 900, far = (k % 2 ? -1 : 1) * (90 + k * 40), y0 = head + 10 - k * 9;
      out.push(div().absolute().left(0).top(y0).size(14).rounded_full().bg("#9ff3ff33")
        .loop("left", { from: -7, to: far, period: per })
        .loop("top", { from: y0, to: y0 - 22, period: per / 3 })
        .child(div().absolute().left(4).top(4).size(6).rounded_full().bg("#e6fdff")
          .loop("opacity", { from: 0.6, to: 1, period: 500 + k * 90 })));
    }
    const says = []; // short bubbles, stacked upwards so they never cover each other
    // git commit: a wax seal pops over the head, "Sealed!"
    if (recent(s?.commitT, 4000)) {
      out.push(image(`${ART}/ic-parchemin.svg`).absolute().left(-9).top(head - 30).size(18)
        .loop("top", { from: head - 24, to: head - 34, period: 1400 }));
      says.push([tr("sealed"), C.goldLight, C.woodDark]);
    }
    // git push: a carrier pigeon takes off east and flies out of the village
    const P = CREATURES.pigeon;
    if (P && recent(s?.pushT, 7000)) {
      const f0 = P.vol0, f1 = P.vol1;
      out.push(div().absolute().left(0).top(head - 10).w(0).h(0)
        .loop("left", { from: 0, to: 900, period: 7000, easing: "linear" })
        .loop("top", { from: head - 10, to: head - 120, period: 7000, easing: "linear" })
        .child(image(`${CRE}/pigeon/vol1-g${sfx}.png`).absolute().left(-f1.w / 2).top(-f1.h / 2).w(f1.w).h(f1.h).loop("opacity", { from: 7, to: -6, period: 240, easing: "linear" }))
        .child(image(`${CRE}/pigeon/vol0-g${sfx}.png`).absolute().left(-f0.w / 2).top(-f0.h / 2).w(f0.w).h(f0.h)
          .loop("opacity", { from: -6, to: 7, period: 240, easing: "linear" })));
      if (Date.now() - s.pushT < 3500) says.push([tr("sent"), C.parch, C.woodDark]);
    }
    // test result (5 s, whatever the scene)
    if (recent(s?.essai?.t, RESULT)) {
      says.push(s.essai.ok ? [tr("testsOk"), "#d9f2c4", "#2f5a1c"] : [tr("testsKo"), C.parch, C.wax]);
    }
    says.forEach(([text, bg, fg], i) => out.push(bubble(text, bg, fg, 14, head - 8 - i * 24)));
    // the hero is hit by a failed tool (lasts 1.5 s)
    if (s?.errT && (s.err ?? 0) > 0 && Date.now() - s.errT < 1500) {
      out.push(div().absolute().left(-26).top(-14).w(52).h(28).rounded_full().bg("#ff3b3044").loop("opacity", { from: 0.2, to: 1, period: 180 }));
      out.push(div().absolute().left(-36).top(head - 8).h(20).px(5).rounded(3).bg(C.parch).border_2().border_color(C.wax)
        .flex().items_center().font_family(UI).text_size(15).text_color(C.wax).whitespace_nowrap().child(tr("ouch")));
    }
    return out;
  }

  /** The creature a fighting unit faces, as its own depth-sorted world element: { z, el } or null. */
  creature(u, night) {
    const addr = u.a.address;
    if (u.leg || this.off) return null;
    const s = this.file(addr) ?? u.a.demoAct;
    if (!s) return null;
    const sc = this.scene(addr);
    const dummy = sc === "test" || recent(s.essai?.t, RESULT);
    if (sc !== "combat" && !dummy) return null;
    // on the hero's right and a little nearer the viewer, facing it (left side near the world's right end)
    const side = u.x > 2700 ? -1 : 1;
    const off = !dummy && boss(s) ? 78 : 44; // the troll is wide: keep it off the hero
    const x = Math.round(u.x + side * off), y = Math.round(u.y + 16);
    const kids = dummy ? this.dummy(u, s, night ? "-n" : "", side) : this.fight(u, s, night ? "-n" : "", side);
    const el = div().absolute().left(x).top(y).w(0).h(0).children(kids);
    return { z: y + 3, el };
  }

  /** The training dummy: struck while the tests run, knocked over when they pass. */
  dummy(u, s, sfx, side) {
    const D = CREATURES.mannequin;
    if (!D) return [];
    const g = side > 0 ? "" : "-g";
    const at = (pose) => { const p = D[pose]; return image(`${CRE}/mannequin/${pose}${g}${sfx}.png`).absolute().left(-p.ax).top(-p.ay + 4).w(p.w).h(p.h); };
    if (recent(s.essai?.t, RESULT)) return [at(s.essai.ok ? "abattu" : "pret")];
    const per = 900 + (hash(u.a.address) % 300);
    return [at("pret").loop("opacity", { from: 7, to: -6, period: per, easing: "linear" }), at("touche").loop("opacity", { from: -6, to: 7, period: 900 + (hash(u.a.address) % 300), easing: "linear" })];
  }

  /** The creature (drawn at its own feet point), its blows and the puff of the last one felled. */
  fight(u, s, sfx, side) {
    const addr = u.a.address;
    const h = this.hits.get(addr) ?? { coups: s.coups ?? 0, at: 0, felled: [] };
    const B = blowsFor(s);
    const sp = boss(s) ? "troll" : species(addr, s.tache ?? 0, Math.floor((s.coups ?? 0) / B), clsOf(u.a));
    const D = CREATURES[sp];
    if (!D) return [];
    const g = side > 0 ? "" : "-g";
    const gap = 0;
    const now = Date.now();
    const hit = now - h.at < 900;
    const out = [];
    const sprite = (pose, extra) => {
      const p = D[pose];
      return image(`${CRE}/${sp}/${pose}${g}${sfx}.png`).absolute().left(side * gap - p.ax).top(-p.ay + 4).w(p.w).h(p.h).when(Boolean(extra), extra);
    };
    if (hit) {
      out.push(sprite("touche"));
      // impact flash on the creature
      out.push(div().absolute().left(side * gap - 6).top(-D.pret.h / 2 - 4).size(12).rounded_full().bg("#fff6d8")
        .loop("opacity", { from: 1, to: 0, period: 450 }));
    } else {
      // ready / attack, alternating: one frame shown at a time (two clamped opacity loops in step)
      out.push(sprite("pret", (el) => el.loop("opacity", { from: 7, to: -6, period: 1700 + (hash(addr) % 400), easing: "linear" })));
      out.push(sprite("attaque", (el) => el.loop("opacity", { from: -6, to: 7, period: 1700 + (hash(addr) % 400), easing: "linear" })));
    }
    // blows left: little pips over the creature
    const left = B - ((s.coups ?? 0) % B);
    out.push(div().absolute().left(side * gap - 2.5 * B).top(-D.pret.h - 6).flex().gap(1)
      .children(Array.from({ length: B }, (_, i) => div().w(4).h(3).bg(i < left ? "#e5685a" : "#3a2a2a").border_1().border_color("#000000"))));
    // the last creature felled: fades and rises in a puff
    for (const f of h.felled) {
      const F = CREATURES[f.species];
      if (!F) continue;
      const p = F.touche;
      out.push(image(`${CRE}/${f.species}/touche${g}${sfx}.png`).absolute().left(side * (gap + 14) - p.ax).top(-p.ay).w(p.w).h(p.h)
        .loop("opacity", { from: 0.9, to: 0, period: 1200 }).loop("top", { from: -p.ay, to: -p.ay - 16, period: 1200 }));
      out.push(div().absolute().left(side * (gap + 14) - 12).top(-20).size(24).rounded_full().bg("#e8e2d0aa")
        .loop("opacity", { from: 0.8, to: 0, period: 1200 }));
    }
    return out;
  }
}

/** A parchment bubble over the hero. */
function bubble(text, bg, fg, size, top) {
  return div().absolute().left(16).top(top).h(20).px(6).rounded(3).bg(bg).border_2().border_color(C.woodDark)
    .flex().items_center().font_family(UI).text_size(size + 1).text_color(fg).whitespace_nowrap().child(text);
}

/** The creature for a task: drawn from the task number and the hero, one per BLOWS edits. */
export function species(addr, tache, n, cls = "mage") {
  const pool = (cls !== "mage" && DISTRICT[HOME[cls]]) || SPECIES;
  return pool[hash(`${addr}:${tache}:${n}`) % pool.length];
}
