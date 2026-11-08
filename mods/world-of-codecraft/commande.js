// The command panel (left part of the bottom strip), drawn for place.js: a carved oak frame,
// "Map of Valbrume" (the minimap from place.js, in a small iron frame), the « Animations »
// toggle, and "Selected unit": the focused hero full-length in a gold portrait frame, name, class,
// state gem, quest, and the Go / Next buttons. The isometric world itself stays in place.js.

import { div } from "gpui-kit";
import { h_flex, v_flex } from "gpui-base";
import { run } from "herdr";
import { CLASSES, RACE_FR, QUEST, heroDesc } from "./kit.js";
import { gradient } from "./kit.js";
import { t } from "./i18n.js";
import { P, frame, frameT, bar, pic, txt, title, button, gem, mark, portraitCard, well } from "./ui.js";

const TONE = { blocked: P.blocked, done: P.done, working: P.working, idle: P.idle, garde: P.guard };
export const MINI_INSET = 38; // the minimap is PANEL - 38 wide (frame 14 x 2 + iron frame 5 x 2)

function heading(text) {
  return div().relative().flex_none().h(30).children(bar("bandeau"))
    .child(div().absolute().left(24).right(24).top(0).bottom(0).flex().items_center().child(title(text, 16, P.goldHi)));
}

function card(sel) {
  if (!sel) {
    return v_flex().flex_1().items_center().justify_center().gap(4)
      .child(txt(t("noUnit"), 16, P.muted, 700))
      .child(txt(t("clickHero"), 14, P.dim, 700));
  }
  const { a, h } = sel;
  const st = a.status;
  const word = QUEST[st]?.mot ?? t("onGuard");
  return h_flex().flex_1().min_h(0).gap(8).px(2).pt(8).items_start()
    .child(portraitCard(h))
    .child(v_flex().flex_1().min_w(0).gap(3)
      .child(title(h.name, 19, P.goldHi).truncate())
      .child(txt(heroDesc(h), 15, P.cream, 700).truncate())
      .child(txt(h.prog, 14, P.muted, 700).truncate())
      .child(h_flex().gap(4).items_center().child(mark(st) ?? gem(st, true)).child(txt(word, 15, TONE[st] ?? P.idle, 800)))
      .when(Boolean(a.tab_name), (el) => el.child(well(div().px(5).py(1).rounded(2), {}).child(txt(t("questTab", a.tab_name), 14, P.parch, 700).truncate())))
      .child(h_flex().gap(6).pt(4)
        .child(button("aller", txt(t("go"), 15, P.cream, 800), () => (a.guard ? run("pane.focus", { pane: a.pane }) : run("agent.focus", { terminal: a.address })), { tip: t("goTip") }))
        .child(button("suivant", [txt(t("next"), 15, P.cream, 800), pic("ic-suivant", 12, 10)], () => run("agent.next", {}), { tip: t("nextTip") }))));
}

/** The whole panel, `width` wide; `minimap` is place.js's minimap element. */
/** The « Animations » toggle: on = animated heroes, walks, activity scenes and enemies; off = still images. */
function toggle(anim) {
  return button("animations", [gem(anim.on ? "working" : "idle", true), txt(t("animations"), 15, P.cream, 800), txt(anim.on ? t("yes") : t("no"), 15, anim.on ? P.working : P.muted, 800)],
    anim.toggle, { tip: anim.on ? t("animOnTip") : t("animOffTip") }).w_full();
}

export function commandPanel(width, minimap, sel, anim = null) {
  const T = frameT("cadre");
  return div().id("commande").relative().flex_none().w(width).h_full().bg(P.leather)
      .child(gradient("#2b1e16", "#100b0a", 165))
    .child(v_flex().absolute().left(T).right(T).top(T).bottom(T).gap(6)
      .child(heading(t("map")))
      .child(div().relative().flex_none().self_start().p(5).bg("#0c0a0e").child(minimap).children(frame("fin")))
      .when(Boolean(anim), (el) => el.child(toggle(anim)))
      .child(heading(t("selected")))
      .child(card(sel)))
    .children(frame("cadre"));
}

// ------------------------------------------------------------------ the panel as its own block

import { image } from "gpui-kit";
import { agents, focused, shared, setShared, props } from "herdr";
import { heroOf, guards, C as KC } from "./kit.js";
import { DEMO_SELECTED } from "./demo.js";
import { WORLD } from "./monde-data.js";

const MONDE = "mods/world-of-codecraft/art/monde";
const DOT = { blocked: KC.quest, done: KC.gold, working: "#7dff6a", idle: "#cfc8da", garde: "#9aa4b1" };

/** Role "commande" (immersive layout): the command panel beside the terminal, under the board. The village
 *  is another block, so the minimap reads its camera and units from the store (wocc.view, written by
 *  place.js) and a click asks it to move there (wocc.goto). */
export class Commande {
  init() { this.w = 262; }

  minimap() {
    const v = shared("wocc.view") ?? { cam: 0, vw: 1200, dots: [] };
    const mw = this.w - MINI_INSET, k = mw / WORLD.w, mh = Math.round(WORLD.h * k);
    return div().id("minicarte").relative().w(mw).h(mh).flex_none().cursor_pointer()
      .tooltip(t("mapTip"))
      .on_mouse_down("left", (e, cx) => {
        const lx = e.local_position?.x;
        if (typeof lx === "number") setShared("wocc.goto", { x: (lx / mw) * WORLD.w, at: Date.now() });
        cx.stop_propagation();
      })
      .child(image(`${MONDE}/minicarte.png`).absolute().left(0).top(0).w(mw).h(mh))
      .children((v.dots ?? []).map(([x, y, st]) => div().absolute().left(x * k - 2).top(Math.min(WORLD.h, Math.max(0, y)) * k - 3).size(4)
        .bg(DOT[st] ?? "#ffffff").border_1().border_color("#000000")))
      .child(div().absolute().left((v.cam / WORLD.w) * mw).top(0).w((v.vw / WORLD.w) * mw).h(mh).border_1().border_color("#ffffff"));
  }

  /** The selected unit, as place.js picks it: the focused agent, else the focused shell. */
  selected() {
    if (props()?.demo) return { a: DEMO_SELECTED, h: heroOf(DEMO_SELECTED.address, DEMO_SELECTED.program) };
    const f = focused();
    const want = f?.agent ?? f?.terminal;
    const a = agents().find((x) => x.address === want)
      ?? guards().map((p) => ({ address: p.terminal, pane: p.pane, guard: true, status: "garde", program: p.program, tab_name: p.title, focused: p.focused })).find((x) => x.address === want);
    return a ? { a, h: heroOf(a.address, a.program) } : null;
  }

  render() {
    const on = shared("wocc.anim") !== false;
    return div().id("commande-bloc").size_full()
      .on_size_change((s, cx) => { if (Math.abs(s.width - this.w) > 2) { this.w = s.width; cx.notify(); } })
      .child(commandPanel(this.w, this.minimap(), this.selected(), { on, toggle: () => setShared("wocc.anim", !on) }));
  }
}
