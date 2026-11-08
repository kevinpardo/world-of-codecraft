// A pane's header: a stitched leather band between iron brackets (gold and topaz when the
// pane has the keyboard). The hero who works in it (framed portrait, name, class, program),
// its quest state as a gem, the folder, and embossed iron buttons: split right, split down,
// zoom, close.

import { div } from "gpui-kit";
import { h_flex } from "gpui-base";
import { panes, props, run } from "herdr";
import { heroOf, heroTitle, CLASSES, RACE_FR, QUEST, folder } from "./kit.js";
import { t } from "./i18n.js";
import { P, bar, txt, gem, mark, portrait, iconButton } from "./ui.js";

const TONE = { blocked: P.blocked, done: P.done, working: P.working, idle: P.idle };

export default class PaneHead {
  init() {}

  render(_cx) {
    const me = props()?.pane;
    const p = panes().find((x) => x.pane === me);
    if (!p) return div().size_full().relative().children(bar("entete"));
    const isHero = Boolean(p.terminal) && (p.status || p.program?.shell);
    const h = isHero ? heroOf(p.terminal, p.program) : null;
    const st = p.status;
    const btn = (ic, cmd, tip, danger) => iconButton(`${ic}-${me}`, ic, () =>
      run(cmd, cmd === "pane.split" ? { pane: me, direction: ic === "split-r" ? "right" : "down" } : { pane: me }), tip, danger);
    const where = folder(p.cwd);
    return div().id(`entete-${me}`).size_full().relative().overflow_hidden()
      .on_click(() => run("pane.focus", { pane: me }))
      .children(bar(p.focused ? "entete-focus" : "entete"))
      .child(h_flex().absolute().left(16).right(16).top(0).h(28).gap(7).items_center()
        .when(Boolean(h), (el) => el.child(portrait(h, 26)))
        .child(txt(h ? heroTitle(h) : p.title || t("scroll"), 16, p.focused ? P.goldHi : P.cream, 800).flex_none())
        .when(Boolean(h), (el) => el.child(txt(`· ${h.prog}`, 14, P.muted, 700).flex_none()))
        .when(Boolean(st), (el) => el.child(h_flex().flex_none().gap(3).items_center().pl(2).pr(6).h(20).rounded(2).bg("#0e0a0ccc")
          .child(mark(st) ?? gem(st, true))
          .child(txt(QUEST[st].mot, 14, TONE[st] ?? P.idle, 800))))
        .child(txt(`${p.status && p.title ? p.title + "  ·  " : ""}${where}${p.branch ? `  ⎇ ${p.branch}` : ""}`, 14, P.dim, 700).flex_1().min_w(0).truncate())
        .child(h_flex().flex_none().gap(3)
          .child(btn("split-r", "pane.split", t("splitR")))
          .child(btn("split-d", "pane.split", t("splitD")))
          .child(btn("zoom", "pane.zoom", t("zoom")))
          .child(btn("close", "pane.close", t("close"), true))));
  }
}
