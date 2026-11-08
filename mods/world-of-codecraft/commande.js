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
