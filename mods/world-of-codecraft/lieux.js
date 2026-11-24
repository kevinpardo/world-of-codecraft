// Where things are in the baked world (art/monde, 3000x400 logical px; 1 art px = 1 logical px).
// Hand-edited: unit spots per building (feet points), building hit boxes (tooltip, double-click to
// recruit), night glows and district banner positions.

import { t } from "./i18n.js";

/** Feet points where the heroes of each class stand while working / blocked / done (first free wins). */
export const SPOTS = {
  tour: [[690, 372], [640, 342], [745, 352], [470, 338], [600, 390]], // mage tower (mage)
  atelier: [[1010, 300], [935, 290], [1060, 272], [820, 296], [1090, 312]], // forge-workshop (artificer)
  caserne: [[2600, 338], [2470, 345], [2700, 318], [2380, 352], [2530, 368], [2660, 366], [2750, 345], [2430, 380]], // barracks (warrior)
  temple: [[2190, 372], [2235, 338], [2110, 388], [2290, 362], [2160, 330]], // temple (priest)
  grange: [[420, 345], [290, 300], [520, 312], [350, 378], [470, 380]], // barn and archery spot (ranger)
  etal1: [[2020, 395], [1735, 320], [1040, 318], [960, 316], [1190, 392]], // market stalls (rogue)
};

/** Building hit boxes [x, y, w, h] and names (in the current language). */
export const BUILDINGS = {
  grange: { get nom() { return t("building").grange; }, box: [70, 75, 220, 200] },
  tour: { get nom() { return t("building").tour; }, box: [505, 15, 110, 350] },
  atelier: { get nom() { return t("building").atelier; }, box: [750, 70, 230, 200] },
  hotel: { get nom() { return t("building").hotel; }, box: [1115, 20, 330, 320] },
  taverne: { get nom() { return t("building").taverne; }, box: [1475, 40, 230, 250] },
  temple: { get nom() { return t("building").temple; }, box: [1890, 10, 270, 350] },
  caserne: { get nom() { return t("building").caserne; }, box: [2330, 100, 240, 220] },
};
/** The market's name in the current language. */
export const market = () => t("market");

/** Night glows [x, y, size, color, period]; shown only at night unless always. */
export const GLOWS = [
  { at: [1598, 345], size: 120, color: "#ffa12b", period: 700, always: true }, // campfire
  { at: [815, 236], size: 60, color: "#ff8a2b", period: 650 }, // forge hearth
  { at: [558, 160], size: 70, color: "#a86bff", period: 2200 }, // tower windows
];

/** Where the district banner hangs for each building [centre x, top y] (hand-placed, world px). */
export const LABELS = {
  tour: [520, 352], atelier: [865, 304], temple: [1990, 366], grange: [180, 280], caserne: [2480, 212], etal1: [1900, 372],
};
