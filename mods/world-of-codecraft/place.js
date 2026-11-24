// La place (bottom strip): Valbrume seen from above, isometric pixel art (direction A, v3).
// Left, the RTS-style command panel: minimap (click to move the camera) and the selected unit.
// Right, the village: the static world (ground, buildings, props, shadows, night lights) is baked
// by tools/bake_world.py into a few big images, day and night, exactly as the approved mocks;
// only the units, their markers, front cut-outs (depth), glows and district banners are live.
//
// Every agent is a hero of its class, standing still at the building of its district (space): the first
// space owns the tower, then the workshop, temple, barn, barracks and stalls, wrapping past six. Status is
// shown by still markers: blocked = red ring + `!` + bubble, done = gold ring + `?`. The village has no
// native loop and no frame timer. While the focused hero works, the strip shows the dungeon instead
// (donjon.js).

import { div, image } from "gpui-kit";
import { h_flex, v_flex } from "gpui-base";
import { agents, spaces, run, setAgentOrder, props, focused, layout, shared, setShared } from "herdr";
import { UI, C, clip, heroOf, heroTitle, district, QUEST, sky, stop, pennant } from "./kit.js";
import { WORLD, TILES, FRONTS } from "./monde-data.js";
import { HEROES } from "./heros-data.js";
import { SPOTS, BUILDINGS, LABELS, market, GLOWS } from "./lieux.js";
import { t as tr, detectLang } from "./i18n.js";
import { Activites } from "./activite.js";
import { Donjon } from "./donjon.js";
import { DEMO_LOG } from "./demo.js";
import { commandPanel, MINI_INSET } from "./commande.js";
import { EXT } from "./terre-data.js";

const ART = "mods/world-of-codecraft/art";
const MONDE = `${ART}/monde`;
const PANEL = 262; // command panel width (lines up with the quest board)
const RANK = { blocked: 0, done: 1, working: 2, idle: 3 };
const LOG_KEY = "wocc.chronicle";

// Buildings in the order districts take them.
const BLD = ["tour", "atelier", "temple", "grange", "caserne", "etal1"];
const RECRUIT = {
  tour: { argv: ["claude"], get what() { return tr("recruit").tour; } },
  atelier: { argv: ["codex"], get what() { return tr("recruit").atelier; } },
  caserne: { argv: null, get what() { return tr("recruit").caserne; } },
};
const RACE_EN = { elfe: "elf", orque: "orc", humain: "human", "mort-vivant": "undead", nain: "dwarf" };
const CLS_EN = { mage: "mage", artificier: "artificer", guerrier: "warrior", pretre: "priest", rodeur: "ranger", voleur: "rogue" };
const RACE_FR = Object.fromEntries(Object.entries(RACE_EN).map(([f, e]) => [e, f]));
const CLS_FR = Object.fromEntries(Object.entries(CLS_EN).map(([f, e]) => [e, f]));
export default class Place {
  init(_p, cx) {
    detectLang(cx);
    this.born = Date.now();
    this.gotoAt = shared("wocc.goto")?.at; // ignore a minimap click left over from an earlier session
    this.w = 1400;
    this.camX = null;
    this.lastFocus = null;
    this.now = new Date();
    this.prev = null;
    this.mob = new Map(); // address -> { goal, group }
    this.act = new Activites(); // what each hero does while working (Claude Code hook)
    this.dg = new Donjon(); // the dungeon view of the working focused hero
    this.dg.load(cx);
    this.live = true; // the « Animations » toggle (shared wocc.anim): off = still dungeon frames, no scenes
    try { this.log = JSON.parse(localStorage.getItem(LOG_KEY) ?? "[]"); } catch { this.log = []; }
    cx.timer.every(60_000, (cx) => { this.now = new Date(); cx.notify(); });
  }

  // ---------------------------------------------------------------- chronicle

  say(text, kind, address) {
    try { this.log = JSON.parse(localStorage.getItem(LOG_KEY) ?? "[]"); } catch {} // the other village may have written
    this.log.unshift({ at: Date.now(), text, kind, address });
    this.log = this.log.slice(0, 40);
    try { localStorage.setItem(LOG_KEY, JSON.stringify(this.log)); } catch {}
  }

  watch(list) {
    const now = new Map(list.map((a) => [a.address, a]));
    if (this.prev) {
      for (const a of list) {
        const was = this.prev.get(a.address);
        const h = heroOf(a.address, a.program);
        const where = this.placeOf(a);
        const quest = a.tab_name && !/^\d+$/.test(a.tab_name) ? tr("quoted", clip(a.tab_name, 34)) : "";
        if (!was) this.say(`[${where}] ${tr("arrives", heroTitle(h), h.prog)}`, a.status, a.address);
        else if (was.status !== a.status) {
          if (a.status === "idle" && was.status === "done") continue;
          const verb = QUEST[a.status].fr + (a.status === "working" || a.status === "done" ? quest : "");
          this.say(`[${where}] ${heroTitle(h)} (${h.prog}) ${verb}`, a.status, a.address);
        }
      }
      for (const [addr, a] of this.prev) if (!now.has(addr)) this.say(`[${tr("gate")}] ${tr("leaves", heroTitle(heroOf(addr, a.program)))}`, "idle", null);
    } else if (!this.log.length) {
      const b = list.filter((a) => a.status === "blocked").length;
      this.say(`[${tr("crier")}] ${tr("hearYe", list.length, b)}`, "idle", null);
    }
    this.prev = new Map(list.map((a) => [a.address, { status: a.status, program: a.program }]));
  }

  // ---------------------------------------------------------------- units

  /** The building of a space: districts take the buildings in order, wrapping past six. */
  bldOf(spaceId) {
    const i = spaces().findIndex((sp) => sp.id === spaceId);
    return BLD[Math.max(0, i) % BLD.length];
  }

  placeOf(a) {
    const k = this.bldOf(a.space);
    return BUILDINGS[k]?.nom ?? market();
  }

  /** Every unit on a free spot of its district's building; a unit keeps its spot while it stays there. */
  units(list) {
    const taken = new Set();
    const goals = new Map();
    const want = list.map((a) => {
      const h = a.demoHero ? { ...heroOf(a.address, a.program), race: RACE_FR[a.demoHero.split("-")[0]], cls: CLS_FR[a.demoHero.split("-")[1]] } : heroOf(a.address, a.program);
      const group = this.bldOf(a.space);
      return { a, h, group, spots: SPOTS[group] };
    });
    for (const u of want) {
      const m = this.mob.get(u.a.address);
      if (m && m.group === u.group && !taken.has(m.goal.join())) { taken.add(m.goal.join()); goals.set(u.a.address, m.goal); }
    }
    for (const u of want) {
      if (goals.has(u.a.address)) continue;
      let g = u.spots.find((p) => !taken.has(p.join()));
      if (!g) { const k = taken.size; const base = u.spots[k % u.spots.length]; g = [base[0] + 18 * (1 + Math.floor(k / u.spots.length)), base[1] + 6]; }
      taken.add(g.join());
      goals.set(u.a.address, g);
    }
    const out = [];
    const alive = new Set();
    for (const u of want) {
      const goal = goals.get(u.a.address);
      alive.add(u.a.address);
      this.mob.set(u.a.address, { goal, group: u.group });
      out.push({ a: u.a, h: u.h, x: goal[0], y: goal[1], key: `${RACE_EN[u.h.race]}-${CLS_EN[u.h.cls]}` });
    }
    for (const k of [...this.mob.keys()]) if (!alive.has(k)) this.mob.delete(k);
    return out;
  }

  /** The pose a unit shows (only its first frame), and its sprite info (falls back to the standing sprite). */
  anim(u) {
    const H = HEROES[u.key];
    const name = u.a.status === "working" ? "work" : "idle";
    const info = H?.anims?.[name];
    if (info) return { name, info, frames: true };
    return { name: "stand", info: H?.stand ?? { w: 50, h: 85, ax: 25, ay: 83 }, frames: false };
  }

  unit(u, selected, night) {
    const { a, h } = u;
    const st = a.status;
    const an = this.anim(u);
    const { w, h: hh, ax, ay } = an.info;
    const suffix = night ? "-n" : "";
    // everything hangs from the feet point
    let el = div().id(`unite-${a.address}`).absolute().left(u.x).top(u.y).w(0).h(0);
    // rings under the feet
    if (selected) el = el.child(image(`${MONDE}/ring-selected.png`).absolute().left(-30).top(-17).w(60).h(33));
    if (st === "blocked") el = el.child(image(`${MONDE}/ring-blocked.png`).absolute().left(-30).top(-17).w(60).h(33));
    if (st === "done") el = el.child(image(`${MONDE}/ring-done.png`).absolute().left(-30).top(-17).w(60).h(33));

    const sprite = an.frames ? `${ART}/heros/${u.key}/${an.name}/00${suffix}.png` : `${ART}/heros/${u.key}/stand${suffix}.png`;
    el = el.child(div().absolute().left(-ax).top(-ay).w(w).h(hh).child(image(sprite).absolute().left(0).top(0).w(w).h(hh)));

    // hit box, tooltip, click
    el = el.child(div().id(`clic-${a.address}`).absolute().left(-ax).top(-ay).w(w).h(hh).cursor_pointer()
      .tooltip(tr("unitTip", heroTitle(h), h.prog, `${a.space_name ?? ""} › ${a.tab_name ?? ""}`, QUEST[st]?.mot ?? st))
      .on_mouse_down("left", stop)
      .on_click(() => run("agent.focus", { terminal: a.address })));

    const head = -ay;
    if (st === "blocked") {
      el = el.child(image(`${MONDE}/m-blocked.png`).absolute().left(-12).top(head - 42).w(24).h(38));
      el = el.child(div().absolute().left(18).top(head - 4).h(22).px(6).rounded(3).bg(C.parch).border_2().border_color(C.woodDark)
        .flex().items_center().whitespace_nowrap().font_family(UI).text_size(15).text_color(C.wax).child(tr("help")[0]));
    }
    if (st === "done") el = el.child(image(`${MONDE}/m-done.png`).absolute().left(-14).top(head - 42).w(28).h(38));
    if (selected) {
      el = el.child(div().absolute().left(-15).top(head - 9).w(30).h(5).bg("#1b1420").border_1().border_color("#000000")
        .child(div().h_full().w(st === "blocked" ? 8 : 28).bg(st === "blocked" ? "#e5685a" : "#7dff6a")));
    }
    return el;
  }

  hidden() {
    const id = props()?.immersion ? "place-immersion" : "place"; // two villages in the layout, one shown
    const find = (n) => (!n || typeof n !== "object" ? null : n.id === id ? n : (n.children ?? []).map(find).find(Boolean) ?? null);
    try { return Boolean(find(layout())?.hidden); } catch { return false; }
  }

  // ---------------------------------------------------------------- world parts

  glows(nightK) {
    if (nightK <= 0) return [];
    return GLOWS.map((g) => {
      const s = g.size;
      return div().absolute().left(g.at[0] - s / 2).top(g.at[1] - s / 2).size(s).rounded_full().bg(`${g.color}22`)
        .opacity(nightK);
    });
  }

  /** A small banner with the district name by each building that a district owns (shared names are joined). */
  labels() {
    const owners = new Map();
    spaces().forEach((sp, i) => {
      const k = BLD[i % BLD.length];
      const d = district(sp);
      if (!owners.has(k)) owners.set(k, { d, names: [] });
      owners.get(k).names.push(d.nom);
    });
    return [...owners].filter(([k]) => LABELS[k]).map(([k, { d, names }]) => {
      const [x, y] = LABELS[k];
      return div().id(`nom-${k}`).absolute().left(x - 120).top(y).w(240).flex().justify_center()
        .child(div().flex().items_center().gap(5).h(24).px(7).rounded(3).bg(C.parch).border_2().border_color(C.woodDark)
          .child(pennant(d.color, d.charge, 1))
          .child(div().font_family(UI).text_size(16).text_color(C.woodInk).whitespace_nowrap().child(clip(names.join(" · "), 22))));
    });
  }

  hitboxes() {
    return Object.entries(BUILDINGS).map(([k, b]) => {
      const r = RECRUIT[k];
      let el = div().id(`bat-${k}`).absolute().left(b.box[0]).top(b.box[1]).w(b.box[2]).h(b.box[3])
        .tooltip(r ? tr("recruitTip", b.nom, r.what) : b.nom);
      if (r) el = el.on_click((e) => { if (e.click_count === 2) run("tab.new", r.argv ? { argv: r.argv } : {}); });
      return el;
    });
  }

  /** A front cut-out (the object's own baked pixels), crossfaded like the world. */
  front(f, nightK) {
    let el = div().absolute().left(f.x).top(f.y).w(f.w).h(f.h);
    if (nightK < 1) el = el.child(image(`${MONDE}/avant-${f.key}-jour.png`).absolute().left(0).top(0).w(f.w).h(f.h));
    if (nightK > 0) el = el.child(image(`${MONDE}/avant-${f.key}-nuit.png`).absolute().left(0).top(0).w(f.w).h(f.h).opacity(nightK));
    return el;
  }

  // ---------------------------------------------------------------- the panel

  /** Immersive layout: the command panel is another block (commande.js, role "commande"). Tell it where the
   *  camera and the units are (store key wocc.view, only when it changes, at most every 300 ms) and obey its
   *  minimap clicks (wocc.goto). */
  bridge(units, vw) {
    const g = shared("wocc.goto");
    if (g && g.at !== this.gotoAt) {
      this.gotoAt = g.at;
      this.camX = g.x - vw / 2;
      if (typeof g.y === "number") this.camY = g.y;
      this.manual = true;
    }
    const view = { cam: Math.round(this.cam(vw)), vw: Math.round(vw), dots: units.map((u) => [Math.round(u.x / 8) * 8, Math.round(u.y / 8) * 8, u.a.status]) };
    const key = JSON.stringify(view);
    const now = Date.now();
    if (key !== this.viewKey && now - (this.viewAt ?? 0) > 300) { this.viewKey = key; this.viewAt = now; setShared("wocc.view", view); }
  }

  minimap(units, vw) {
    const mw = PANEL - MINI_INSET, k = mw / WORLD.w, mh = Math.round(WORLD.h * k);
    const col = { blocked: C.quest, done: C.gold, working: "#7dff6a", idle: "#cfc8da" };
    const view = (vw / WORLD.w) * mw;
    const vx = (this.cam(vw) / WORLD.w) * mw;
    return div().id("minicarte").relative().w(mw).h(mh).flex_none().cursor_pointer()
      .tooltip(tr("mapTip"))
      .on_mouse_down("left", (e, cx) => {
        const lx = e.local_position?.x;
        if (typeof lx === "number") { this.camX = (lx / mw) * WORLD.w - vw / 2; this.manual = true; cx.notify(); }
        cx.stop_propagation();
      })
      .child(image(`${MONDE}/minicarte.png`).absolute().left(0).top(0).w(mw).h(mh))
      .children(units.map((u) => {
        return div().absolute().left(u.x * k - 2).top(u.y * k - 3).size(4).bg(col[u.a.status] ?? "#ffffff").border_1().border_color("#000000");
      }))
      .child(div().absolute().left(vx).top(0).w(view).h(mh).border_1().border_color("#ffffff"));
  }

  /** Immersive layout: the world y at the top of the view, kept inside the painted bands. */
  camV() {
    const h = this.h ?? WORLD.h, top = -EXT.nord, bottom = WORLD.h + EXT.sud;
    if (h >= bottom - top) return (top + bottom - h) / 2;
    const c = this.camY ?? (WORLD.h / 2 - 40 - h / 2);
    return Math.max(top, Math.min(bottom - h, c));
  }

  cam(vw) {
    const max = Math.max(0, WORLD.w - vw);
    const c = this.camX ?? (WORLD.w / 2 - vw / 2);
    return Math.max(0, Math.min(max, c));
  }

  chronicle() {
    const tone = { blocked: C.quest, done: C.gold, working: "#8fd16a", idle: "#cfc8da" };
    return v_flex().absolute().left(10).top(8).gap(2).children((props()?.demo ? DEMO_LOG : this.log).slice(0, 4).map((e, i) => {
      const tag = e.text.match(/^\[[^\]]+\]/)?.[0] ?? "";
      const d = new Date(e.at);
      return h_flex().id(`ev-${i}-${e.at}`).gap(5).px(6).h(20).items_center().rounded(2).bg("#0b0810bb").whitespace_nowrap().cursor_pointer()
        .opacity(i === 0 ? 1 : 0.9 - i * 0.15)
        .on_mouse_down("left", stop)
        .on_click(() => { if (e.address) run("agent.focus", { terminal: e.address }); })
        .font_family(UI).text_size(16)
        .child(div().text_color("#8a8296").child(`${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`))
        .child(div().text_color(tone[e.kind] ?? C.gold).child(tag))
        .child(div().text_color(C.cream).child(e.text.slice(tag.length).trim()));
    }));
  }

  // ---------------------------------------------------------------- demo (props.demo)

  demo() {
    const sp = spaces()[0];
    // [status, program, hero]: the animated heroes first, then fallbacks
    const D = [["working", "claude", "orc-mage"], ["blocked", "shell", "human-warrior"], ["done", "opencode", "elf-ranger"], ["idle", "codex", "dwarf-artificer"],
      ["working", "gemini", "human-priest"], ["working", "claude", "elf-mage"], ["blocked", "aider", "undead-rogue"], ["working", "codex", "orc-artificer"],
      ["working", "claude", "human-mage"], ["working", "claude", "undead-mage"]];
    // demo activities (props.demo): combat with a blow every 2.5 s and a failed tool every 20 s, a scout with
    // two familiars, a meditation, a thinker; the scene changes immediately (no file, no anti-zapping wait)
    const n = Date.now();
    const ACT = {
      0: { act: "code", tache: 1, coups: Math.floor(n / 2500) % 400, subs: 0, err: 1, errT: n - (n % 20000), t: n },
      5: { act: "eclaire", tache: 1, subs: 2, t: n },
      7: { act: "test", tache: 1, essai: { ok: Math.floor(n / 12000) % 2 === 0, t: n - (n % 12000) }, commitT: n - (n % 15000), pushT: n - (n % 30000), t: n },
      8: { act: "pense", tache: 1, subs: 1, t: n },
      9: { act: "code", tache: 7, coups: Math.floor(n / 3100) % 400, subs: 0, errTache: 3, t: n }, // the troll boss
      4: { act: "medite", tache: 1, subs: 0, t: n },
    };
    const cyc = props()?.demo === "marche" ? Math.floor(Date.now() / 30000) % 2 : 0;
    return D.map(([status, key, hero], i) => ({
      address: `demo-${i}-${key}`, space: sp?.id, space_name: sp?.name, tab_name: tr("demoTabs")[i],
      status: cyc && i < 4 ? (status === "idle" ? "working" : "idle") : status, seq: i, focused: false, demoHero: hero, demoAct: ACT[i],
      program: { key: key === "shell" ? "sh" : key, name: key, shell: false } }));
  }

  /** The village scene as [world, chronicle], bottom to top: ground, glows, hitboxes, units with front cut-outs (by depth), district banners, chronicle. */
  village(units, sel, { vw, camX, imm, nightK, nightHeroes }) {
    // depth: units by feet y (+3, like the compositor), front cut-outs above the units behind them
    const things = units.map((u) => ({ z: u.y + 3, el: this.unit(u, u === sel, nightHeroes) }));
    for (const fr of FRONTS) {
      const over = units.some((u) => {
        const an = this.anim(u);
        const x0 = u.x - an.info.ax, y0 = u.y - an.info.ay;
        return u.y + 3 < fr.z && x0 < fr.x + fr.w && x0 + an.info.w > fr.x && y0 < fr.y + fr.h && u.y > fr.y;
      });
      if (over) things.push({ z: fr.z, el: this.front(fr, nightK) });
    }
    things.sort((p, q) => p.z - q.z);

    // immersive layout: the lands around the village (tools/bake_lands.py, terre-data.js) and a vertical camera too
    const worldTop = imm ? -this.camV() : Math.round(((this.h ?? WORLD.h) - WORLD.h) / 2);
    const glide = this.drag ? { duration: 16, easing: "linear" } : { duration: 650, easing: "ease-in-out" };
    const band = (name, y) => [
      ...EXT.tiles.map((k) => image(`${MONDE}/${name}-${k}-jour.png`).absolute().left(k * 1000).top(y).w(1000).h(EXT[name])),
      ...(nightK > 0 ? EXT.tiles.map((k) => image(`${MONDE}/${name}-${k}-nuit.png`).absolute().left(k * 1000).top(y).w(1000).h(EXT[name]).opacity(nightK)) : []),
    ];

    // the camera glides (650 ms) except while the view is dragged, where it follows the pointer
    const layer = (id) => div().id(id).absolute().top(worldTop).left(-camX).w(WORLD.w).h(WORLD.h)
      .transition("left", glide).transition("top", glide);
    const world = layer("monde")
      .when(imm, (el) => el.children(band("nord", -EXT.nord)).children(band("sud", WORLD.h)))
      .children(TILES.map((tl) => image(`${MONDE}/jour-${tl.k}.png`).absolute().left(tl.x).top(0).w(tl.w).h(WORLD.h)))
      .when(nightK > 0, (el) => el.children(TILES.map((tl) => image(`${MONDE}/nuit-${tl.k}.png`).absolute().left(tl.x).top(0).w(tl.w).h(WORLD.h).opacity(nightK))))
      .children(this.glows(nightK))
      .children(this.hitboxes())
      .children(things.map((th) => th.el))
      .children(this.labels());

    return [world, this.chronicle()];
  }

  render(cx) {
    const at = new Date(this.now);
    if (typeof props()?.heure === "number") at.setHours(props().heure, 0); // demo: another time of day
    const sk = sky(at);
    const nightK = sk.phase === "nuit" ? 1 : sk.phase === "jour" ? 0 : 0.55; // night layer over the day one
    const nightHeroes = sk.phase === "nuit";

    this.live = shared("wocc.anim") !== false;
    const hidden = this.hidden();
    let list = agents().map((a) => ({ ...a }));
    if (props()?.demo) list = this.demo(); // screenshots: only the demo heroes, none of the person's agents
    else if (hidden) { // the other village keeps the chronicle; start afresh when shown again
      this.prev = null;
      try { this.log = JSON.parse(localStorage.getItem(LOG_KEY) ?? "[]"); } catch {}
    } else if (shared("wocc.lang") || Date.now() - this.born > 4000) this.watch(list); // chronicle once the language is known
    const order = [...list].sort((a, b) => RANK[a.status] - RANK[b.status] || b.seq - a.seq);
    if (!props()?.demo) setAgentOrder(order.map((a) => a.address));
    const units = this.units(order);

    // the selected unit = the focused agent (none while a shell is focused)
    const f = focused();
    const sel = units.find((u) => u.a.address === (f?.agent ?? f?.terminal)) ?? units.find((u) => u.a.focused) ?? null;
    // immersive layout: the command panel is its own block (role "commande"), the village takes the full width
    const imm = Boolean(props()?.immersion);
    const vw = Math.max(200, this.w - (imm ? 0 : PANEL));
    if (imm) this.bridge(units, vw);
    if (sel && sel.a.address !== this.lastFocus) {
      this.lastFocus = sel.a.address;
      this.manual = false; // a new selection takes the camera back
      this.camX = sel.x - vw / 2; // glide to the selected unit
      if (imm) this.camY = sel.y - 60 - (this.h ?? WORLD.h) / 2; // and bring the village back into view
    }
    const camX = this.cam(vw);

    // the dungeon replaces the village while the focused hero works (not in immersion mode)
    const dungeon = !imm && !hidden && sel?.a.status === "working";
    this.act.watch(cx, order, !dungeon, !this.live);
    this.act.watchCtx(cx, imm || hidden ? null : sel?.a.address);
    this.dg.sync(cx, dungeon, { sel, act: this.act, live: this.live });

    const scene = dungeon ? [] : this.village(units, sel, { vw, camX, imm, nightK, nightHeroes });

    const panel = imm ? null : commandPanel(PANEL, this.minimap(units, vw), sel, { on: this.live, toggle: () => setShared("wocc.anim", !this.live) });

    return h_flex().id("place").size_full().bg(C.slate)
      .on_size_change((s, cx) => {
        if (Math.abs(s.width - this.w) > 10 || s.height !== this.h) { this.w = s.width; this.h = s.height; cx.notify(); }
      })
      .when(!imm, (el) => el.child(panel))
      .child(div().id("vue").flex_1().h_full().relative().overflow_hidden().bg("#3f6b2c")
        .on_scroll_wheel((e, cx) => {
          if (imm) { this.camX = this.cam(vw) - e.delta.x; this.camY = this.camV() - e.delta.y; }
          else this.camX = this.cam(vw) - (Math.abs(e.delta.x) > Math.abs(e.delta.y) ? e.delta.x : e.delta.y);
          this.manual = true;
          cx.notify();
        })
        // click and drag the village to pan (units and buttons stop the press, so their clicks still work)
        .when(!this.drag, (e) => e.cursor_grab()).when(Boolean(this.drag), (e) => e.cursor_grabbing())
        .on_mouse_down("left", (e, cx) => { this.drag = { x0: e.position.x, y0: e.position.y, cam0: this.cam(vw), camY0: this.camV() }; cx.notify(); })
        .on_mouse_move((e, cx) => {
          if (!this.drag) return;
          const x = Math.max(0, Math.min(Math.max(0, WORLD.w - vw), this.drag.cam0 - (e.position.x - this.drag.x0)));
          const y = imm ? this.drag.camY0 - (e.position.y - this.drag.y0) : 0;
          if (Math.abs(x - this.cam(vw)) < 1 && (!imm || Math.abs(y - this.camV()) < 1)) return;
          this.camX = x;
          if (imm) this.camY = y;
          this.manual = true;
          cx.notify();
        })
        .on_mouse_up("left", (_e, cx) => { if (this.drag) { this.drag = null; cx.notify(); } })
        .on_hover((over, cx) => { if (!over && this.drag) { this.drag = null; cx.notify(); } })
        .children(scene)
        .when(dungeon, (el) => el.child(this.dg.view(vw, this.h ?? 400))));
  }
}
