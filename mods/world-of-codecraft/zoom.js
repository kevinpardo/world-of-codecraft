// World zoom for the immersive layout: the village is drawn in world units (1 art px = 1 unit) and
// shown Z times bigger. GPUI has no scale transform, so the world's builders come from here: zdiv(),
// zimage(), zsvg() return elements whose lengths are multiplied by Z (positions, sizes, paddings,
// gaps, radii, text sizes, and left/top/width/height in loops and transitions). Children and
// `.when` callbacks are handled, so a whole world element tree scales by changing only the builders.
// Z = 1 returns the plain elements: no cost in the normal layout.
// Call unwrap(el) before handing a zoomed element to a plain one (the layer that holds the world).

import { div, image, svg } from "gpui-kit";

let Z = 1;
export const setZoom = (z) => { Z = z; };
export const zoom = () => Z;

const RAW = Symbol("raw");
const LENGTHS = new Set(["left", "top", "right", "bottom", "w", "h", "size", "min_w", "min_h", "max_w", "max_h",
  "p", "px", "py", "pl", "pr", "pt", "pb", "m", "mx", "my", "ml", "mr", "mt", "mb", "gap", "text_size", "rounded"]);
const MOTION = new Set(["left", "top", "width", "height"]);

export const unwrap = (x) => (x && x[RAW]) || x;

function wrap(el) {
  if (Z === 1 || !el || typeof el !== "object" || el[RAW]) return el;
  return new Proxy(el, {
    get(target, prop) {
      if (prop === RAW) return target;
      const v = target[prop];
      if (typeof v !== "function") return v;
      return (...args) => {
        if (LENGTHS.has(prop)) args = args.map((a) => (typeof a === "number" ? a * Z : a));
        else if ((prop === "loop" || prop === "transition") && MOTION.has(args[0]) && args[1] && typeof args[1] === "object" && "from" in args[1]) {
          args[1] = { ...args[1], from: args[1].from * Z, to: args[1].to * Z };
        } else if (prop === "child") args[0] = unwrap(args[0]);
        else if (prop === "children") args[0] = Array.from(args[0] ?? [], unwrap);
        else if (prop === "when" && typeof args[1] === "function") { const f = args[1]; args[1] = (e) => unwrap(f(wrap(e))); }
        else if (prop === "map" && typeof args[0] === "function") { const f = args[0]; args[0] = (e) => unwrap(f(wrap(e))); }
        const r = v.apply(target, args);
        return r && typeof r === "object" ? wrap(r) : r;
      };
    },
  });
}

export const zdiv = () => wrap(div());
export const zimage = (src) => wrap(image(src));
export const zsvg = (src) => wrap(svg(src));
