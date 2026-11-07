// The pediment (top bar, window drag): a carved oak beam with iron straps and a gold bead.
// Left, the crest and title in a gold cartouche. Then ornate plaques, strategy-game
// style: Gold = Claude account A, Wood = account B (left this week, the 5-hour window under
// it), Heroes = agents at work / in the village, Fair = the next weekly reset.
// Gold, Wood and Fair are an optional cduo integration: they only appear when the quota
// files exist (see readQuotas in kit.js); without them the header shows Heroes only. In the middle,
// the district's banner and a parchment scroll with the district and quest. On the right,
// the waiting-heroes button (click: go to the next one), then the hour plaque.

import { div } from "gpui-kit";
import { h_flex, v_flex } from "gpui-base";
import { spaces, agents, run, window as appWindow } from "herdr";
import { VILLAGE, district, clip, heroOf, heroTitle, hourName, hhmm, isNight, readQuotas, left } from "./kit.js";
import { P, DECO, TEXTE, bar, pic, txt, button, mark, banner } from "./ui.js";

const PW = 136; // plaque width

export default class Fronton {
  init(_p, cx) {
    this.now = new Date();
    this.q = [];
    const tick = (cx) => {
      this.now = new Date();
      cx.spawn(async (cx) => { this.q = await readQuotas(); cx.notify(); });
    };
    tick(cx);
    cx.timer.every(60_000, tick);
  }

  /** An ornate plaque: icon in its gold socket, the value, a caption. */
  plaque(id, icon, main, sub, tip, warn) {
    return div().id(id).relative().flex_none().w(PW).h(40).tooltip(tip)
      .child(pic("plaque", PW, 40).absolute().left(0).top(0))
      .child(div().absolute().left(4).top(4).w(32).h(32).flex().items_center().justify_center().child(icon))
      .child(v_flex().absolute().left(42).top(4).bottom(4).right(8).justify_center().gap(0)
        .child(txt(main, 18, warn ? P.blocked : P.cream, 800).line_height(1.05))
        .when(Boolean(sub), (el) => el.child(txt(sub, 13, P.muted, 700).line_height(1.05).truncate())));
  }

  quota(acc, label, icon) {
    const q = this.q.find((x) => x.acc === acc) ?? { missing: true };
    if (q.missing || !q.week) return null; // no quota file: no plaque at all
    const rem = Math.max(0, 100 - q.week.used);
    const five = q.five ? `5h: ${100 - q.five.used}%` : `account ${acc}`;
    const tip = `${label} = Claude account ${acc}\n${rem}% left this week (fair in ${left(q.week.resets) || "?"})${q.five ? `\n5-hour window: ${100 - q.five.used}% left${q.five.resets ? ` (${left(q.five.resets)})` : ""}` : ""}${q.stale ? "\nReading older than 30 min" : ""}`;
    return this.plaque(`res-${acc}`, icon, `${rem}%${q.stale ? " ?" : ""}`, five, tip, rem <= 20);
  }

  render(_cx) {
    const sp = spaces().find((s) => s.active);
    const tab = sp?.tabs.find((t) => t.active);
    const d = sp ? district(sp) : null;
    const all = agents();
    const blocked = all.filter((a) => a.status === "blocked");
    const done = all.filter((a) => a.status === "done");
    const busy = all.filter((a) => a.status === "working").length;
    const win = appWindow();
    const mac = (win?.platform ?? "macos") === "macos" && !win?.fullscreen;
    const night = isNight(this.now);
    const resets = this.q.map((q) => q.week?.resets).filter(Boolean);
    const fair = resets.length ? left(Math.min(...resets)) : "";
    const gold = this.quota("A", "Gold", pic("ic-or", 32, 24));
    const wood = this.quota("B", "Wood", pic("ic-bois", 36, 28));

    const waiting = blocked.length ? blocked : done;
    let alert = null;
    if (waiting.length) {
      const isB = blocked.length > 0;
      const h = heroOf(waiting[0].address, waiting[0].program);
      alert = button("alerte", [
        mark(isB ? "blocked" : "done"),
        txt(waiting.length > 1 ? `${waiting.length} ${isB ? "waiting" : "quests to turn in"}` : `${h.name} ${isB ? "is waiting" : "is done"}`, 16, isB ? P.goldHi : P.cream, 800),
      ], () => run("agent.focus", { terminal: waiting[0].address }), {
        face: isB ? "or" : "", h: 28,
        tip: `${heroTitle(h)} ${isB ? "awaits your orders" : "is back from a quest"} (click: go there)`,
      });
    }

    // the district's banner and the parchment scroll (flat vellum behind the text)
    const scroll = d && h_flex().id("rouleau").tooltip(`${d.titre}${tab ? `\nQuest: ${tab.name}` : ""}`).flex_shrink(1).min_w(0).max_w(620).h(44).gap(4).items_center()
      .child(div().flex_none().h(40).mt(2).child(banner(d)))
      .child(div().relative().flex_shrink(1).min_w(0).h(34).pl(16).pr(16).flex().items_center().overflow_hidden()
        .children(bar("rouleau"))
        .child(h_flex().relative().min_w(0).gap(8).items_center()
          .child(txt(tab ? d.num : `${d.num} · ${d.nom}`, 16, P.ink2, 800).flex_none())
          .when(Boolean(tab), (e) => e
            .child(txt("›", 16, P.inkSoft, 800).flex_none())
            .child(txt(clip(tab.name, 44), 16, P.wax, 800).min_w(0).truncate()))));

    const hour = div().id("heure").relative().flex_none().w(170).h(40)
      .tooltip(`${hourName(this.now)} (canonical hour) · ${night ? "night" : "day"}`)
      .child(pic("plaque-l", 170, 40).absolute().left(0).top(0))
      .child(div().absolute().left(10).top(10).child(pic(night ? "ic-lune" : "ic-soleil", 20, 20)))
      .child(h_flex().absolute().left(42).right(10).top(0).bottom(0).items_center().justify_between()
        .child(txt(hourName(this.now), 16, P.parch, 700))
        .child(txt(hhmm(this.now), 20, P.goldHi, 800)));

    return div().id("fronton").size_full().relative().overflow_hidden().bg(P.well)
      .children(bar("poutre"))
      .child(h_flex().absolute().left(mac ? 84 : 10).right(10).top(0).h(44).gap(8).items_center()
        // crest and title in their cartouche
        .child(div().relative().flex_none().w(284).h(42)
          .child(pic("cartouche", 284, 42).absolute().left(0).top(0))
          .child(div().absolute().left(10).top(3).child(pic("blason", 30, 36)))
          .child(v_flex().absolute().left(46).top(0).bottom(0).justify_center()
            .child(div().font_family(DECO).font_weight(700).text_size(17).line_height(1.1).text_color(P.goldHi).child("World of Codecraft"))
            .child(txt(`village of ${VILLAGE}`, 13, P.muted, 700).line_height(1.1))))
        .when(Boolean(gold), (el) => el.child(gold))
        .when(Boolean(wood), (el) => el.child(wood))
        .child(this.plaque("res-heros", pic("ic-heros", 26, 22), `${busy} / ${all.length}`, "heroes at work", `${busy} heroes at work, ${all.length} agents in the village`))
        .when(resets.length > 0, (el) => el.child(this.plaque("res-foire", pic("ic-sablier", 22, 28), fair || "—", "until the fair", "The fair: the weekly reset of the Claude quotas")))
        .child(div().flex_1().min_w(0).flex().justify_center().when(Boolean(scroll), (el) => el.child(scroll)))
        .when(Boolean(alert), (el) => el.child(alert))
        .child(hour));
  }
}
