// The dungeon view: replaces the village in the bottom strip while the focused hero works.
// The room (art/donjon/salle.png, 1600x400) is centred and cropped; the hero stands at the anchor its
// scene asks for (art/donjon/meta.json, with built-in fallbacks) and the scene's foe, dummy or shelf is
// drawn beside it. Frames swap on ONE data timer (6 fps) that redraws only when a visible frame changes;
// no native loop is used, so the strip stays quiet.

import { div, image } from "gpui-kit";
import { v_flex } from "gpui-base";
import { appHome, readTextFile } from "herdr";
import { UI, C, heroTitle, hash, healthBar } from "./kit.js";
import { HEROES } from "./heros-data.js";
import { CREATURES } from "./creatures-data.js";
import { species, boss, blowsFor, clsOf, recent, RESULT } from "./activite.js";
import { t as tr } from "./i18n.js";

const ART = "mods/world-of-codecraft/art";
const DJ = `${ART}/donjon`;
const CRE = `${ART}/creatures`;
const ROOM = { w: 1600, h: 400 };
const FPS = 6; // the frame timer's rate
const SC = 2; // sprites are drawn at twice their logical size
const TICK = 1000 / FPS;
const ALLY_SC = 1.25; // allies are drawn smaller than the hero
const RACES = ["dwarf", "elf", "human", "orc", "undead"];
const PIGEON = { vol0: [21, 26, 10, 25], vol1: [27, 18, 13, 17] }; // w, h, anchor x, anchor y
const SIDE = [[-110, -20], [-170, -35], [-230, -20], [-290, -35]]; // ally spots left of the hero when meta has none
const FALLBACK = { hero: [620, 330], foe: [860, 330], dummy: [860, 330], shelf: [380, 320], rest: [1120, 330], torches: [], floor: [300, 400] };

/** The hero's pose for a scene. */
function poseOf(scene) {
  if (scene === "pense") return "idle";
  if (scene === "medite") return "rest";
  return "work";
}

/** The anchor a scene stands on. */
function anchorOf(scene) {
  if (scene === "eclaire") return "shelf";
  if (scene === "medite") return "rest";
  return "hero";
}

/** The hero class an ally plays, from its Claude Code agent type. */
function allyClass(type) {
  const n = String(type ?? "").toLowerCase();
  if (/explore|search|fetch|guide/.test(n)) return "ranger";
  if (n === "implementer") return "artificer";
  if (n === "plan") return "priest";
  return "warrior";
}

/** A parchment bubble. */
function bubble(text, bg, fg, left, top) {
  return div().absolute().left(left).top(top).h(22).px(7).rounded(3).bg(bg).border_2().border_color(C.woodDark)
    .flex().items_center().font_family(UI).text_size(16).text_color(fg).whitespace_nowrap().child(text);
}

export class Donjon {
  constructor() {
    this.meta = null; // anchors from meta.json, once read
    this.art = false; // meta.json exists: the art is in place
    this.asked = false;
    this.timer = null;
    this.sig = "";
    this.ctx = null;
    this.invoc = false; // art/donjon/salle-invocation.png is in place
    this.seen = new Map(); // ally key -> when it first appeared
  }

  /** Reads art/donjon/meta.json once; the anchors fall back to the built-in ones. */
  load(cx) {
    if (this.asked) return;
    this.asked = true;
    cx.spawn(async (acx) => {
      let m = null;
      try { m = JSON.parse((await readTextFile(`${appHome()}/${DJ}/meta.json`)) ?? "null"); } catch { m = null; }
      this.art = Boolean(m);
      this.meta = { ...FALLBACK, ...(m ?? {}) };
      this.invoc = Boolean(m) && m.invocation !== false; // the room art ships with salle-invocation.png
      acx.notify();
    });
  }

  anchors() { return this.meta ?? FALLBACK; }

  /** Everything that changes the picture at time t; the timer redraws when this changes. */
  state(t) {
    const { sel, act, live } = this.ctx;
    const addr = sel.a.address;
    const scene = act.scene(addr);
    const s = act.file(addr) ?? sel.a.demoAct ?? null;
    const info = HEROES[sel.key]?.anims?.[poseOf(scene)];
    const fps = info ? Math.min(FPS, info.fps) : 0;
    const h = act.hits.get(addr);
    const res = recent(s?.essai?.t, RESULT);
    const st = { scene, f: Math.floor(t / TICK), k: live && info ? Math.floor((t / 1000) * fps) % info.n : 0, res, ok: Boolean(s?.essai?.ok) };
    if (!live) return st;
    st.torch = Math.floor(t / 280) % 2;
    st.hitk = h && t - h.at < 900 ? Math.floor((t - h.at) / 150) : -1;
    st.hit = st.hitk >= 0;
    st.felled = h?.felled.length ?? 0;
    st.puffk = h?.felled.length ? Math.floor((t - h.felled[0].at) / 200) : -1;
    st.alt = Math.floor(t / 850) % 2;
    st.web = s?.act === "web";
    st.hurt = Boolean(s?.errT && (s.err ?? 0) > 0 && t - s.errT < 1500);
    st.sealed = recent(s?.commitT, 4000);
    st.sealK = st.sealed ? Math.floor((t - s.commitT) / TICK) : -1;
    st.sent = recent(s?.pushT, 3500);
    st.pushK = st.sent ? Math.floor((t - s.pushT) / TICK) : -1;
    st.allies = this.allies(s, t);
    st.nAllies = Math.max(s?.subs ?? 0, st.allies.length);
    st.ctx = this.ctx.act.ctxLeft(addr);
    return st;
  }

  /** The visible allies (up to 4): sprite key, name, idle frame and summon-ring stage at time t. */
  allies(s, t) {
    const { sel } = this.ctx;
    const raw = s?.allies?.length ? s.allies : Array.from({ length: s?.subs ?? 0 }, () => ({ id: "", type: "" }));
    const mine = sel.key.split("-")[0];
    const alive = new Set();
    const out = [];
    raw.slice(0, 4).forEach((a, i) => {
      const id = a.id || `#${i}`;
      alive.add(id);
      let r = hash(a.id || `${a.type}#${i}`) % RACES.length;
      if (RACES[r] === mine) r = (r + 1) % RACES.length;
      const key = `${RACES[r]}-${allyClass(a.type)}`;
      const info = HEROES[key]?.anims?.idle;
      if (!info) return;
      if (!this.seen.has(id)) this.seen.set(id, t);
      const age = t - this.seen.get(id);
      out.push({ key, name: a.type, k: Math.floor((t / 1000) * Math.min(FPS, info.fps)) % info.n, ring: age < 700 ? Math.floor(age / 117) : -1 });
    });
    for (const id of [...this.seen.keys()]) if (!alive.has(id)) this.seen.delete(id);
    return out;
  }

  /** Starts or stops the one frame timer. */
  sync(cx, shown, ctx) {
    this.ctx = ctx;
    const need = shown && ctx.live;
    if (need && !this.timer) {
      this.timer = cx.timer.every(Math.round(1000 / FPS), (cx) => {
        if (!this.ctx) return;
        const sig = JSON.stringify(this.state(Date.now()));
        if (sig !== this.sig) { this.sig = sig; cx.notify(); }
      });
    } else if (!need && this.timer) { this.timer.cancel(); this.timer = null; }
  }

  /** A sprite stack: every frame stacked (preloaded), only the current one shown. */
  stack(files, w, h, ax, ay, k, sc = SC, op = 1) {
    return div().absolute().left(-ax * sc).top(-ay * sc).w(w * sc).h(h * sc)
      .children(files.map((f, i) => image(f).absolute().left(0).top(0).w(w * sc).h(h * sc).opacity(i === k ? op : 0)));
  }

  /** A spectral ally at its feet point: violet glow, translucent idle sprite, name tag, summon ring. */
  ally(a, x, y) {
    const info = HEROES[a.key].anims.idle;
    const files = Array.from({ length: info.n }, (_, i) => `${ART}/heros/${a.key}/idle/${String(i).padStart(2, "0")}-g.png`);
    const d = 30 + a.ring * 26;
    return div().absolute().left(x).top(y).w(0).h(0)
      .child(div().absolute().left(-40).top(-9).w(80).h(18).rounded_full().bg("#8a7bff55"))
      .child(this.stack(files, info.w, info.h, info.w - info.ax, info.ay, a.k, ALLY_SC, 0.7))
      .when(Boolean(a.name), (el) => el.child(div().absolute().left(-50).top(6).w(100).flex().justify_center()
        .child(div().px(4).rounded(3).bg("#1c1430cc").font_family(UI).text_size(13).text_color("#e0d6ff").whitespace_nowrap().child(a.name))))
      .when(a.ring >= 0, (el) => el.child(div().absolute().left(-d / 2).top(-d * 0.2 - 8).w(d).h(d * 0.4).rounded_full().border_2().border_color("#c4b4ff").opacity(1 - a.ring / 6)));
  }

  /** A small spark at (x, y), centred. */
  spark(x, y, size, op = 1) {
    return image(`${ART}/etincelle.svg`).absolute().left(x - size / 2).top(y - size / 2).size(size).opacity(op);
  }

  /** Effects of the scene around the hero's feet point; `head` is the top of the sprite (negative). */
  heroFx(st, head) {
    const out = [];
    if (st.scene === "eclaire") out.push(...this.archives(st, head));
    if (st.scene === "medite") out.push(...this.trance(f, head));
    if (st.sealK >= 0) {
      out.push(div().absolute().left(-11).top(head - 44 - Math.min(st.sealK, 6) * 4).size(22).rounded_full().bg(C.wax).border_2().border_color("#6e1319")
        .child(div().absolute().left(5).top(5).size(8).rounded_full().bg(C.gold)));
    }
    if (st.pushK >= 0) {
      const [w, h, ax, ay] = PIGEON[st.pushK % 2 ? "vol1" : "vol0"];
      const file = st.pushK % 2 ? "vol1" : "vol0";
      out.push(image(`${CRE}/pigeon/${file}-g.png`).absolute().left(20 + st.pushK * 22 - ax * SC).top(head - 10 - st.pushK * 3 - ay * SC).w(w * SC).h(h * SC));
    }
    return out;
  }

  /** Reading and searching: a floating tome, rising sparkles and, for the web, a scrying orb. */
  archives(st, head) {
    const f = st.f;
    const bob = [0, -3, -5, -3][f % 4];
    const out = [div().absolute().left(40).top(head + 14 + bob).flex()
      .child(div().w(18).h(24).bg(C.parch).border_2().border_color(C.woodDark).flex().flex_col().gap(3).p(3).child(div().h(2).bg(C.inkSoft)).child(div().h(2).bg(C.inkSoft)))
      .child(div().w(18).h(24).bg(C.parchDark).border_2().border_color(C.woodDark).flex().flex_col().gap(3).p(3).child(div().h(2).bg(C.inkSoft)).child(div().h(2).bg(C.inkSoft)))];
    for (let k = 0; k < 4; k++) {
      const ph = (f + k * 3) % 12;
      out.push(this.spark(40 + 4 + k * 10 + [0, 3, 0, -3][(f + k) % 4], head + 8 - ph * 4, 12, 1 - ph / 12));
    }
    if (st.web) {
      out.push(div().absolute().left(100).top(head + 30 + bob).size(22).rounded_full().bg("#7fd0ff").border_2().border_color("#2b5f8a")
        .child(div().absolute().left([3, 9, 11, 6][f % 4]).top([4, 3, 9, 11][f % 4]).size(5).rounded_full().bg("#ffffff")));
    }
    return out;
  }

  /** Compacting: a halo, four runes orbiting in 30-degree steps and a pulsing crystal. */
  trance(f, head) {
    const out = [image(`${ART}/halo.svg`).absolute().left(-68).top(-70).w(136).h(80).opacity(0.6)];
    const cy = head / 2;
    for (let k = 0; k < 4; k++) {
      const a = ((f * 30 + k * 90) * Math.PI) / 180;
      out.push(this.spark(Math.cos(a) * 70, cy + Math.sin(a) * 26, 20));
    }
    out.push(div().absolute().left(-5).top(head - 26 + [0, -2, -4, -2][f % 4]).w(10).h(16).rounded(2).bg("#c9a7ff").border_1().border_color("#5b2ca8").opacity(f % 6 < 3 ? 1 : 0.6));
    return out;
  }

  hero(st) {
    const { sel } = this.ctx;
    const pose = poseOf(st.scene);
    const H = HEROES[sel.key];
    const info = H?.anims?.[pose];
    if (info) return this.stack(Array.from({ length: info.n }, (_, i) => `${ART}/heros/${sel.key}/${pose}/${String(i).padStart(2, "0")}-g.png`), info.w, info.h, info.w - info.ax, info.ay, st.k);
    const s = H?.stand ?? { w: 50, h: 85, ax: 25, ay: 83 };
    return this.stack([`${ART}/heros/${sel.key}/stand.png`], s.w, s.h, s.ax, s.ay, 0);
  }

  /** The foe or dummy of a scene at its anchor: { el, name, blows } or null. */
  foe(st, s, at) {
    const { sel, act } = this.ctx;
    const addr = sel.a.address;
    const dummy = st.scene === "test" || (st.scene !== "combat" && st.res);
    if (!dummy && st.scene !== "combat") return null;
    if (dummy) {
      const D = CREATURES.mannequin;
      if (!D) return null;
      let pose = st.alt ? "touche" : "pret";
      if (st.res) pose = st.ok ? "abattu" : "pret";
      const p = D[pose];
      const kids = [image(`${CRE}/mannequin/${pose}.png`).absolute().left(-p.ax * SC).top(-p.ay * SC).w(p.w * SC).h(p.h * SC)];
      if (st.res && st.ok) {
        for (let k = 0; k < 5; k++) kids.push(this.spark((k - 2) * 18, -70 - ((st.f + k * 2) % 8) * 7, 14, 1 - ((st.f + k * 2) % 8) / 8));
      }
      return { el: div().absolute().left(at[0]).top(at[1]).w(0).h(0).children(kids) };
    }
    const B = blowsFor(s ?? {});
    const sp = boss(s) ? "troll" : species(addr, s?.tache ?? 0, Math.floor((s?.coups ?? 0) / B), clsOf(sel.a));
    const D = CREATURES[sp];
    if (!D) return null;
    const pose = st.hit ? "touche" : st.alt ? "attaque" : "pret";
    const p = D[pose];
    const kids = [image(`${CRE}/${sp}/${pose}.png`).absolute().left(-p.ax * SC).top(-p.ay * SC).w(p.w * SC).h(p.h * SC)];
    if (st.hit) {
      const mid = -D.pret.h * SC / 2, fl = 22 - st.hitk * 3;
      kids.push(div().absolute().left(-fl / 2).top(mid - fl / 2).size(fl).rounded_full().bg("#fff6d8"));
      for (let k = 0; k < 6; k++) {
        const a = (k * 60 * Math.PI) / 180, r = 14 + st.hitk * 10;
        kids.push(this.spark(Math.cos(a) * r, mid + Math.sin(a) * r, 10, 1 - st.hitk / 6));
      }
    }
    const left = B - ((s?.coups ?? 0) % B);
    kids.push(div().absolute().left(-3.5 * B).top(-D.pret.h * SC - 10).flex().gap(1)
      .children(Array.from({ length: B }, (_, i) => div().w(6).h(4).bg(i < left ? "#e5685a" : "#3a2a2a").border_1().border_color("#000000"))));
    // the last creature felled stays as a faded ghost until its puff ends
    if (st.felled && !st.hit) {
      const f = CREATURES[act.hits.get(addr)?.felled[0]?.species];
      if (f) kids.push(image(`${CRE}/${act.hits.get(addr).felled[0].species}/touche.png`).absolute().left(14 - f.touche.ax * SC).top(-f.touche.ay * SC - 12).w(f.touche.w * SC).h(f.touche.h * SC).opacity(Math.max(0.1, 0.5 - st.puffk * 0.08)));
      const r = 12 + st.puffk * 8;
      for (let k = 0; k < 3; k++) kids.push(div().absolute().left(14 + (k - 1) * r - r / 2).top(-f.touche.h * SC / 2 - r / 2 - (k % 2) * 8).size(r).rounded_full().bg("#d8d4dc").opacity(Math.max(0, 0.6 - st.puffk * 0.1)));
    }
    return { el: div().absolute().left(at[0]).top(at[1]).w(0).h(0).children(kids), name: boss(s) ? tr("djBoss") : null, left, B };
  }

  /** The hero card: name and title, activity, combat progress. */
  hud(st, foe) {
    const { sel } = this.ctx;
    const D = tr("dj");
    const act = D[st.scene ?? "travail"] ?? D.travail;
    return v_flex().absolute().left(12).top(10).gap(1).px(9).py(5).rounded(3).bg(C.parch).border_2().border_color(C.woodDark).font_family(UI)
      .child(div().text_size(18).text_color(C.woodInk).whitespace_nowrap().child(heroTitle(sel.h)))
      .child(div().text_size(15).text_color(C.inkSoft).whitespace_nowrap().child(act))
      .when(st.ctx != null, (el) => el.child(healthBar(st.ctx, 110, tr("hp"))))
      .when(st.nAllies > 0, (el) => el.child(div().text_size(14).text_color("#7a5ac8").whitespace_nowrap().child(tr("djAllies", st.nAllies))))
      .when(Boolean(foe?.B), (el) => el.child(div().text_size(14).text_color(C.wax).whitespace_nowrap().child(foe.name ? `${foe.name} · ${tr("djFoe", foe.left)}` : tr("djFoe", foe.left))));
  }

  /** Bubbles over the hero's head, stacked upwards. */
  bubbles(st, x, top) {
    const says = [];
    if (st.scene === "pense") says.push([["·", "· ·", "· · ·", "· · ·"][Math.floor((st.f ?? 0) / 3) % 4], C.parch, C.woodDark, [0, -2, -4, -2][(st.f ?? 0) % 4]]);
    if (st.sealed) says.push([tr("sealed"), C.goldLight, C.woodDark]);
    if (st.sent) says.push([tr("sent"), C.parch, C.woodDark]);
    if (st.res) says.push(st.ok ? [tr("testsOk"), "#d9f2c4", "#2f5a1c"] : [tr("testsKo"), C.parch, C.wax]);
    if (st.hurt) says.push([tr("ouch"), C.parch, C.wax]);
    return says.map(([text, bg, fg, dy = 0], i) => bubble(text, bg, fg, x, top - i * 26 + dy));
  }

  /** The dungeon as a box filling its parent (vw x vh). */
  view(vw, vh) {
    const st = this.state(Date.now());
    this.sig = JSON.stringify(st);
    const M = this.anchors();
    const { sel } = this.ctx;
    const s = this.ctx.act.file(sel.a.address) ?? sel.a.demoAct ?? null;
    const ox = Math.round((vw - ROOM.w) / 2), oy = Math.round((vh - ROOM.h) / 2);
    const at = (p) => [ox + p[0], oy + p[1]];
    const [hx, hy] = at(M[anchorOf(st.scene)]);
    const foe = this.foe(st, s, at(st.scene === "test" || (st.scene !== "combat" && st.res) ? M.dummy : M.foe));
    const info = HEROES[sel.key]?.anims?.[poseOf(st.scene)] ?? HEROES[sel.key]?.stand ?? { ay: 83 };
    const head = hy - info.ay * SC;
    const al = st.allies ?? [];
    const room = al.length && this.invoc ? "salle-invocation" : "salle";
    const spots = M.allies?.length ? M.allies.map(at) : SIDE.map(([dx, dy]) => [hx + dx, hy + dy]);
    return div().id("donjon").absolute().left(0).top(0).size_full().overflow_hidden().bg(al.length && !this.art ? "#241638" : "#14121a")
      .when(this.art, (el) => el.child(image(`${DJ}/${room}.png`).absolute().left(ox).top(oy).w(ROOM.w).h(ROOM.h)))
      .when(al.length > 0 && Boolean(M.circle), (el) => el.child(div().absolute().left(at(M.circle)[0] - 110).top(at(M.circle)[1] - 24).w(220).h(48).rounded_full().bg("#8a7bff33")))
      .children((M.torches ?? []).map(([x, y]) => image(`${ART}/${st.torch ? "flamme-b" : "flamme-a"}.svg`).absolute().left(ox + x - 9).top(oy + y - 24).w(18).h(29)))
      .children(al.map((a, i) => ({ a, p: spots[i] ?? spots[0] })).sort((u, v) => u.p[1] - v.p[1]).map(({ a, p }) => this.ally(a, p[0], p[1])))
      .child(div().absolute().left(hx - (st.hurt && st.f % 2 ? 4 : 0)).top(hy).w(0).h(0)
        .when(st.hurt, (el) => el.child(div().absolute().left(-50).top(-26).w(100).h(52).rounded_full().bg("#ff3b3044").opacity(st.f % 2 ? 1 : 0.5)))
        .child(this.hero(st))
        .children(this.heroFx(st, -info.ay * SC)))
      .when(Boolean(foe), (el) => el.child(foe.el))
      .children(this.bubbles(st, hx + 24, head - 4))
      .child(this.hud(st, foe));
  }
}
