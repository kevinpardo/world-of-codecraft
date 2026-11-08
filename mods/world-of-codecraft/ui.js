// World of Codecraft: the interface kit. Pixel-art pieces drawn by tools/ui.py (art/ui/),
// composed here. Herdr has no 9-slice and no image tiling, so a frame is four corners plus
// four long edge strips, each strip cropped (never stretched) by an overflow-hidden box: the
// strips are uniform along their length, so they fit any size, crisp, with no seam.

import { div, image } from "gpui-kit";
import { h_flex } from "gpui-base";

export const UIA = "mods/world-of-codecraft/art/ui";

// fonts (OFL, in fonts/): Cinzel for titles, Alegreya Sans for everything you read
export const DECO = "Cinzel Decorative";
export const TITRE = "Cinzel";
export const TEXTE = "Alegreya Sans";

// the interface palette (same ramps as the art: warm lights, violet shadows)
export const P = {
  ink: "#120c10", night: "#17111a", enamel: "#231b27", enamelHi: "#2e2433", leather: "#1d1410", well: "#140e0b",
  cream: "#f6ead0", parch: "#e9d9b4", muted: "#cdb98f", dim: "#9a8a72", faint: "#6f6252",
  gold: "#f2c25a", goldHi: "#ffe39a", goldLo: "#b47a22", bronze: "#8a6334",
  ink2: "#2e2016", inkSoft: "#5e4630", wax: "#9c2230",
  working: "#6fdc78", blocked: "#ff6a52", done: "#f6c24a", idle: "#b9b1d2", guard: "#a8b4c4",
};

const META = {
  cadre: { C: 34, t: 14, L: 2400 }, baguette: { C: 14, t: 14, L: 2400 },
  fin: { C: 10, t: 5, L: 2400 }, "fin-or": { C: 10, t: 5, L: 2400 }, "fin-rubis": { C: 10, t: 5, L: 2400 },
  poutre: { C: 24, H: 48, L: 3600 }, entete: { C: 16, H: 30, L: 2400 }, "entete-focus": { C: 16, H: 30, L: 2400 },
  bandeau: { C: 20, H: 30, L: 2400 }, rouleau: { C: 14, H: 34, L: 2400 },
  "btn-n": { C: 8, H: 28, L: 800 }, "btn-h": { C: 8, H: 28, L: 800 }, "btn-p": { C: 8, H: 28, L: 800 },
  "btn-or-n": { C: 8, H: 28, L: 800 }, "btn-or-h": { C: 8, H: 28, L: 800 }, "btn-or-p": { C: 8, H: 28, L: 800 },
};

export const art = (name) => `${UIA}/${name}.png`;
/** A pixel-art image at its logical size. */
export const pic = (name, w, h) => image(art(name)).w(w).h(h).flex_none();

const crop = (name, w, h) => image(art(name)).absolute().left(0).top(0).w(w).h(h);

/** The pieces of a frame, as absolute layers for a `.relative()` box. */
export function frame(kind) {
  const { C, t, L } = META[kind];
  return [
    div().absolute().left(C).right(C).top(0).h(t).overflow_hidden().child(crop(`${kind}-t`, L, t)),
    div().absolute().left(C).right(C).bottom(0).h(t).overflow_hidden().child(crop(`${kind}-b`, L, t)),
    div().absolute().top(C).bottom(C).left(0).w(t).overflow_hidden().child(crop(`${kind}-l`, t, L)),
    div().absolute().top(C).bottom(C).right(0).w(t).overflow_hidden().child(crop(`${kind}-r`, t, L)),
    image(art(`${kind}-tl`)).absolute().left(0).top(0).size(C),
    image(art(`${kind}-tr`)).absolute().right(0).top(0).size(C),
    image(art(`${kind}-bl`)).absolute().left(0).bottom(0).size(C),
    image(art(`${kind}-br`)).absolute().right(0).bottom(0).size(C),
  ];
}
export const frameT = (kind) => META[kind].t;

/** The layers of a horizontal bar of any width: left cap, cropped middle, right cap. */
export function bar(kind) {
  const { C, H, L } = META[kind];
  return [
    div().absolute().left(C).right(C).top(0).h(H).overflow_hidden().child(crop(`${kind}-m`, L, H)),
    image(art(`${kind}-l`)).absolute().left(0).top(0).w(C).h(H),
    image(art(`${kind}-r`)).absolute().right(0).top(0).w(C).h(H),
  ];
}

/** One rail of the frame around the terminals (a thin layout block on each side). */
export function rail(side) {
  const k = "baguette", { C, t, L } = META[k];
  if (side === "left" || side === "right") {
    return div().size_full().relative().overflow_hidden().child(crop(`${k}-${side === "left" ? "l" : "r"}`, t, L));
  }
  const e = side === "top" ? "t" : "b";
  return div().size_full().relative().overflow_hidden()
    .child(div().absolute().left(C).right(C).top(0).h(t).overflow_hidden().child(crop(`${k}-${e}`, L, t)))
    .child(image(art(`${k}-${e}l`)).absolute().left(0).top(0).size(C))
    .child(image(art(`${k}-${e}r`)).absolute().right(0).top(0).size(C));
}

/** Text in the interface's faces. */
export const txt = (s, size = 16, color = P.cream, weight = 700) =>
  div().font_family(TEXTE).font_weight(weight).text_size(size).text_color(color).child(String(s ?? ""));
export const title = (s, size = 18, color = P.goldHi) =>
  div().font_family(TITRE).font_weight(700).text_size(size).text_color(color).child(String(s ?? ""));

/**
 * An embossed button: iron (or the gold-and-red alert face), lit edge on hover, pushed when
 * pressed. The hover layer holds the pressed image under the lit one; pressing hides the lit one.
 */
export function button(id, content, onClick, { face = "", w = null, h = 28, tip = null, stopDrag = true } = {}) {
  const f = face ? `btn-${face}-` : "btn-";
  let el = h_flex().id(id).relative().flex_none().h(h).px(12).gap(6).items_center().justify_center().cursor_pointer();
  if (w) el = el.w(w);
  el = el
    .child(div().absolute().left(0).top(0).size_full().children(bar(`${f}n`)))
    .child(div().id(`${id}-survol`).absolute().left(0).top(0).size_full().opacity(0).hover((s) => s.opacity(1))
      .child(div().absolute().left(0).top(0).size_full().children(bar(`${f}p`)))
      .child(div().id(`${id}-lueur`).absolute().left(0).top(0).size_full().active((s) => s.opacity(0)).children(bar(`${f}h`))))
    .child(h_flex().relative().gap(6).items_center().children(Array.isArray(content) ? content : [content]));
  if (stopDrag) el = el.on_mouse_down("left", (_e, cx) => cx.stop_propagation());
  if (tip) el = el.tooltip(tip);
  return el.on_click(onClick);
}

/** A square iron icon button (pane controls), 24 x 22. */
export function iconButton(id, icon, onClick, tip, danger) {
  return div().id(id).relative().flex_none().w(24).h(22).cursor_pointer()
    .on_mouse_down("left", (_e, cx) => cx.stop_propagation())
    .tooltip(tip)
    .child(pic("bouton-n", 24, 22).absolute().left(0).top(0))
    .child(div().id(`${id}-survol`).absolute().left(0).top(0).size_full().opacity(0).hover((s) => s.opacity(1))
      .child(pic("bouton-p", 24, 22).absolute().left(0).top(0))
      .child(div().id(`${id}-lueur`).absolute().left(0).top(0).size_full().active((s) => s.opacity(0)).child(pic("bouton-h", 24, 22))))
    .child(pic(`ic-${icon}`, 13, 11).absolute().left(danger ? 6 : 5).top(5))
    .on_click(onClick);
}

/** A status gem (working emerald, blocked ruby, done topaz, idle moonstone); blocked flashes. */
export function gem(st, small = false) {
  const s = small ? 15 : 18;
  if (!["working", "blocked", "done", "idle"].includes(st)) return div().size(s).flex_none();
  let g = pic(`gemme-${st}${small ? "-s" : ""}`, s, s);
  if (st === "blocked") g = g.loop("opacity", { from: 0.35, to: 1, period: 520 });
  if (st === "done") g = g.loop("opacity", { from: 0.7, to: 1, period: 1400 });
  return g;
}

/** The quest mark: a flashing yellow "!" (blocked) or a glowing gold "?" (done). */
export function mark(st) {
  if (st === "blocked") return pic("marque-quete", 9, 16).loop("opacity", { from: 0.3, to: 1, period: 520 });
  if (st === "done") return pic("marque-rendu", 11, 16).loop("opacity", { from: 0.65, to: 1, period: 1400 });
  return null;
}

const CLOTH = ["#7a1f2b", "#2f4a7a", "#2f6b4a", "#6b3a8a", "#8a5a1f", "#1f6b6b", "#8a2f5a", "#4a5a2f"];
/** A district's banner: cloth in its colour, its charge in gold (26 x 40). */
export const banner = (d, scale = 1) =>
  pic(`banniere-${Math.max(0, CLOTH.indexOf(d.color))}-${d.charge}`, 26 * scale, 40 * scale);

/** A hero's framed portrait: 22 (lists) or 26 (pane headers). */
export const portrait = (h, size = 22) => pic(`heros/${h.race}-${h.cls}-p${size === 26 ? 26 : 22}`, size === 26 ? 26 : 22, size === 26 ? 26 : 22);
/** A hero full-length in a gold frame (66 x 98), for the unit card. */
export const portraitCard = (h) => pic(`heros/${h.race}-${h.cls}-carte`, 66, 98);

/** A flat enamel well behind text: no texture, a lit lower edge and a dark upper one (inset). */
export function well(el, { bg = P.enamel, dark = "#0c080c", lit = "#4a3a2e" } = {}) {
  return el.relative().bg(bg)
    .child(div().absolute().left(0).right(0).top(0).h(1).bg(dark))
    .child(div().absolute().left(0).top(0).bottom(0).w(1).bg(dark))
    .child(div().absolute().left(0).right(0).bottom(0).h(1).bg(lit))
    .child(div().absolute().right(0).top(0).bottom(0).w(1).bg(lit));
}
