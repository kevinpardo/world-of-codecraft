// The board (left column): every district (space) of the village at a glance, in a carved
// oak frame with gold corners. Each district is a small iron-framed card (gold when shown,
// red lacquer when a hero needs you) with, without clicking: its banner and name, how many
// sessions (terminals) and heroes (agents) it holds, a count per state (gems: on a quest /
// help / to turn in / resting), then each of its quests (tabs) on one line with its state and
// the portraits of its heroes. Text always sits on flat enamel or parchment, never on texture.
// Click a district: go there; a quest line: show that quest.

import { div } from "gpui-kit";
import { h_flex, v_flex } from "gpui-base";
import { spaces, agents, run } from "herdr";
import { district, clip, heroOf } from "./kit.js";
import { gradient } from "./kit.js";
import { P, TITRE, frame, frameT, bar, pic, txt, title, button, gem, mark, banner, portrait, well } from "./ui.js";

const ORDER = ["blocked", "done", "working", "idle"];
const STATE = {
  blocked: { mot: "need help", color: P.blocked },
  done: { mot: "to turn in", color: P.done },
  working: { mot: "on a quest", color: P.working },
  idle: { mot: "resting", color: P.idle },
};
const plural = (n, one, many) => `${n} ${n > 1 ? many : one}`;

export default class Tableau {
  heading(text, extra) {
    return div().relative().flex_none().h(30)
      .children(bar("bandeau"))
      .child(h_flex().absolute().left(24).right(24).top(0).bottom(0).gap(8).items_center()
        .child(title(text, 17, P.goldHi).flex_1())
        .when(Boolean(extra), (e) => e.child(txt(extra, 14, P.muted, 700))));
  }

  // One state counter: a gem, the number, the word, on a flat enamel well.
  chip(st, n) {
    const s = STATE[st];
    const b = st === "blocked";
    return well(h_flex().flex_none().h(22).pl(3).pr(7).gap(3).items_center().rounded(2),
      { bg: b ? "#4a1418" : P.night, lit: b ? "#a0303a" : "#3e3040" })
      .child(gem(st, true))
      .child(txt(`${n} ${s.mot}`, 14, b ? "#ffd8cc" : P.parch, 700));
  }

  quest(sp, tab, heroes) {
    const st = tab.status;
    const on = sp.active && tab.active;
    const name = tab.named ? tab.name : (heroes[0]?.title && heroes[0].title !== heroes[0].program?.name ? heroes[0].title : `Quest #${tab.index}`);
    const fg = on ? P.ink2 : st === "blocked" ? "#ffd8cc" : P.cream;
    let line = h_flex().id(`quete-${tab.id}`).relative().h(28).pl(5).pr(4).gap(6).items_center().rounded(2).cursor_pointer()
      .bg(on ? P.parch : st === "blocked" ? "#3a1216" : "#00000000").hover((s) => s.bg(on ? P.parch : "#ffffff10"))
      .tooltip(`Quest ${tab.index}: ${tab.name}${tab.panes > 1 ? ` (${tab.panes} sessions)` : ""} (click: show it)`)
      .on_click(() => { if (!sp.active) run("space.select", { id: sp.id }); run("tab.select", { id: tab.id }); })
      .child(div().w(16).flex_none().flex().justify_center().child(mark(st) ?? (st ? gem(st, true) : div().size(5).rounded(1).bg(on ? P.inkSoft : P.faint))))
      .child(txt(clip(name, 32), 15, fg, on ? 800 : 700).flex_1().min_w(0).truncate())
      .when(tab.panes > 1, (e) => e.child(txt(`×${tab.panes}`, 14, on ? P.inkSoft : P.dim, 700).flex_none()))
      .child(h_flex().flex_none().gap(2).children(heroes.slice(0, 3).map((a) => portrait(heroOf(a.address, a.program), 22))))
      .when(heroes.length > 3, (e) => e.child(txt(`+${heroes.length - 3}`, 14, on ? P.inkSoft : P.dim, 700).flex_none()));
    if (on) line = line.child(div().absolute().left(0).top(0).bottom(0).w(2).bg(P.wax));
    return line;
  }

  district(sp, all) {
    const d = district(sp);
    const heroes = all.filter((a) => a.space === sp.id);
    const tabs = sp.tabs.filter((t) => !t.settled || t.active);
    const sessions = sp.tabs.reduce((n, t) => n + (t.panes || 0), 0);
    const counts = ORDER.map((st) => [st, heroes.filter((a) => a.status === st).length]).filter(([, n]) => n > 0);
    const blocked = heroes.some((a) => a.status === "blocked");
    const kind = blocked ? "fin-rubis" : sp.active ? "fin-or" : "fin";

    // the district's head: banner, name, sessions and heroes, the big counter
    const head = h_flex().id(`quartier-tete-${sp.id}`).h(46).pl(6).pr(4).gap(8).items_center().cursor_pointer()
      .hover((s) => s.bg("#ffffff08"))
      .tooltip(`${d.titre}${sp.machine ? ` @${sp.machine}` : ""} (click: go there)`)
      .on_click(() => run("space.select", { id: sp.id }))
      .child(div().flex_none().mt(-6).child(banner(d)))
      .child(v_flex().flex_1().min_w(0).gap(0)
        .child(txt(`${d.num} · ${d.nom}`, 18, sp.active ? P.goldHi : P.cream, 800).truncate())
        .child(txt(`${plural(sessions, "session", "sessions")} · ${plural(heroes.length, "hero", "heroes")}`, 14, P.muted, 700).truncate()))
      .child(div().relative().flex_none().size(32).tooltip(`${plural(sessions, "session", "sessions")} in this district`)
        .child(pic("medaillon", 32, 32).absolute().left(0).top(0))
        .child(div().absolute().left(0).top(0).size(32).flex().items_center().justify_center()
          .child(div().font_family(TITRE).font_weight(700).text_size(15).text_color(P.goldHi).child(String(sessions)))));

    let inner = v_flex().relative().gap(2).p(6).child(head);
    if (counts.length) inner = inner.child(h_flex().flex_wrap().gap(4).px(2).pb(3).children(counts.map(([st, n]) => this.chip(st, n))));
    inner = inner.child(v_flex().gap(1).children(tabs.map((t) => this.quest(sp, t, heroes.filter((a) => a.tab === t.id)))));

    let card = div().id(`quartier-${sp.id}`).relative().flex_none().mx(2).mt(6)
      .bg(sp.active ? P.enamelHi : P.enamel)
      .child(inner)
      .children(frame(kind));
    if (blocked) card = card.loop("opacity", { from: 0.86, to: 1, period: 900 });
    return card;
  }

  render(_cx) {
    const all = agents();
    const list = spaces();
    const sessions = list.reduce((n, sp) => n + sp.tabs.reduce((m, t) => m + (t.panes || 0), 0), 0);
    const T = frameT("cadre");
    const add = (id, label, tip, fn) => button(id, [pic("ic-plus", 11, 11), txt(label, 15, P.cream, 800)], fn, { tip }).flex_1();
    return div().id("tableau").size_full().relative().bg(P.leather)
      .child(gradient("#2b1e16", "#100b0a", 165))
      .child(v_flex().absolute().left(T).right(T).top(T).bottom(T)
        .child(this.heading("Districts", plural(sessions, "session", "sessions")))
        .child(v_flex().id("quartiers").flex_1().min_h(0).overflow_y_scrollbar().px(2).pb(10)
          .children(list.map((sp) => this.district(sp, all)))
          .child(h_flex().mx(2).mt(10).gap(6)
            .child(add("nouvelle-quete", "Quest", "Start a new quest (a new tab in this district)", () => run("tab.new", {})))
            .child(add("nouveau-quartier", "District", "Found a new district (a new space)", () => run("space.new", {}))))))
      .children(frame("cadre"));
  }
}
