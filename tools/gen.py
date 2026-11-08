#!/usr/bin/env python3
"""Pixel-art generator for the Valbrume village layout (mods/world-of-codecraft/art).
Everything is drawn from rectangles on a pixel grid, outlined automatically, and
written as crisp SVGs (one <rect> per run of same-colored pixels)."""
import os, sys

OUT = os.path.expanduser("~/.config/herdr-app/mods/world-of-codecraft/art")
os.makedirs(OUT, exist_ok=True)
OUTLINE = "#1b1420"


class Px:
    def __init__(s, w, h):
        s.w, s.h = w, h
        s.g = [[None] * w for _ in range(h)]

    def p(s, x, y, c):
        if 0 <= x < s.w and 0 <= y < s.h:
            s.g[y][x] = c

    def r(s, x, y, w, h, c):
        for j in range(y, y + h):
            for i in range(x, x + w):
                s.p(i, j, c)

    def outline(s, c=OUTLINE):
        add = []
        for y in range(s.h):
            for x in range(s.w):
                if s.g[y][x] is None:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        xx, yy = x + dx, y + dy
                        if 0 <= xx < s.w and 0 <= yy < s.h and s.g[yy][xx] not in (None, c):
                            add.append((x, y)); break
        for x, y in add:
            s.g[y][x] = c

    def svg(s, name):
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s.w} {s.h}" width="{s.w}" height="{s.h}" shape-rendering="crispEdges">']
        for y in range(s.h):
            x = 0
            while x < s.w:
                c = s.g[y][x]
                if c is None:
                    x += 1; continue
                x0 = x
                while x < s.w and s.g[y][x] == c:
                    x += 1
                op = ""
                if len(c) == 9:
                    op = f' fill-opacity="{int(c[7:9], 16) / 255:.2f}"'; c = c[:7]
                out.append(f'<rect x="{x0}" y="{y}" width="{x - x0}" height="1" fill="{c}"{op}/>')
        out.append("</svg>")
        open(os.path.join(OUT, name + ".svg"), "w").write("\n".join(out))


# ---------------------------------------------------------------- heroes
RACES = {
    "humain": dict(skin="#e8b48a", skin2="#c98f68", hair="#6b4423", eye="#1d1a22"),
    "elfe": dict(skin="#f2d3ae", skin2="#d9b08a", hair="#ecd57c", eye="#2b6e5a", ears=True),
    "orque": dict(skin="#6f9a4a", skin2="#557a36", hair="#26232a", eye="#1d1a22", tusks=True),
    "mort-vivant": dict(skin="#a3b5ac", skin2="#7c8f87", hair="#454a57", eye="#7ff0ff", undead=True),
    "nain": dict(skin="#e3a57f", skin2="#c0805c", hair="#c0602a", eye="#1d1a22", beard=True),
}
CLASSES = {
    "mage": dict(main="#5b3a9c", shade="#41286f", trim="#e8c35a", robe=True, hat="#4a2f86"),
    "guerrier": dict(main="#9aa4b1", shade="#6b7380", trim="#a33a2e", helm="#8a94a2", legs="#5a3b22"),
    "artificier": dict(main="#2f7f7a", shade="#225d59", trim="#8a5a2b", goggles=True, legs="#4a3a2a"),
    "voleur": dict(main="#33423a", shade="#232e28", trim="#7a1f2b", hood="#2a352f", legs="#2a2a30"),
    "pretre": dict(main="#ece5cf", shade="#c9c0a6", trim="#d9a93a", robe=True, cowl="#d8d0b8"),
    "rodeur": dict(main="#4c7a34", shade="#375a25", trim="#8a5a2b", cap="#6b4a2a", legs="#4a3a2a"),
}


def hero(race, cls, sit=False):
    R, C = RACES[race], CLASSES[cls]
    W, H = 18, 27
    s = Px(W, H)
    dy = 3 if sit else 0
    ox, oy = 1, 2  # margin for outline
    X = lambda x: x + ox
    Y = lambda y: y + oy + dy
    # legs
    legs = C.get("legs", C["shade"])
    if not sit:
        if C.get("robe"):
            s.r(X(4), Y(17), 8, 4, C["main"]); s.r(X(4), Y(20), 8, 1, C["shade"])
            s.r(X(5), Y(21), 2, 1, "#3a2a22"); s.r(X(9), Y(21), 2, 1, "#3a2a22")
        else:
            s.r(X(5), Y(17), 2, 4, legs); s.r(X(9), Y(17), 2, 4, legs)
            s.r(X(4), Y(21), 3, 1, "#2e2018"); s.r(X(9), Y(21), 3, 1, "#2e2018")
    else:
        # seated: thighs forward (to the right), shins down
        base = C["main"] if C.get("robe") else legs
        s.r(X(5), Y(17), 8, 2, base)
        s.r(X(11), Y(19), 2, 1, base); s.r(X(11), Y(20), 3, 1, "#2e2018")
    # torso
    s.r(X(4), Y(11), 8, 6, C["main"])
    s.r(X(4), Y(16), 8, 1, C["shade"])
    s.r(X(7), Y(11), 2, 6, C["trim"] if cls in ("mage", "pretre", "guerrier") else C["main"])
    s.r(X(4), Y(15), 8, 1, C["trim"] if cls in ("artificier", "rodeur", "voleur") else C["shade"])  # belt
    if cls == "artificier":
        s.r(X(5), Y(12), 6, 5, C["trim"]); s.r(X(6), Y(13), 4, 1, "#c99a5a")  # apron
    if cls == "guerrier":
        s.r(X(4), Y(11), 8, 1, "#c7ced8"); s.r(X(3), Y(11), 2, 2, "#c7ced8"); s.r(X(11), Y(11), 2, 2, "#c7ced8")  # pauldrons
    # arms
    s.r(X(3), Y(12), 1, 4, C["shade"]); s.r(X(12), Y(12), 1, 4, C["shade"])
    s.r(X(3), Y(16), 1, 1, R["skin"]); s.r(X(12), Y(16), 1, 1, R["skin"])
    # head
    s.r(X(5), Y(5), 6, 6, R["skin"])
    s.r(X(5), Y(10), 6, 1, R["skin2"])
    s.r(X(5), Y(4), 6, 2, R["hair"]); s.p(X(5), Y(6), R["hair"]); s.p(X(10), Y(6), R["hair"])
    s.p(X(6), Y(7), R["eye"]); s.p(X(9), Y(7), R["eye"])
    if R.get("ears"):
        s.p(X(4), Y(7), R["skin"]); s.p(X(3), Y(6), R["skin"]); s.p(X(11), Y(7), R["skin"]); s.p(X(12), Y(6), R["skin"])
    if R.get("tusks"):
        s.p(X(6), Y(9), "#f4efe0"); s.p(X(9), Y(9), "#f4efe0"); s.r(X(4), Y(6), 1, 3, R["skin"]); s.r(X(11), Y(6), 1, 3, R["skin"])
    if R.get("undead"):
        s.p(X(7), Y(9), "#3d4743"); s.p(X(8), Y(9), "#f0efe6"); s.p(X(6), Y(9), "#f0efe6")
    if R.get("beard"):
        s.r(X(5), Y(9), 6, 3, R["hair"]); s.r(X(6), Y(12), 4, 1, R["hair"]); s.p(X(7), Y(13), R["hair"])
    # headgear
    if C.get("hat"):
        h = C["hat"]
        s.r(X(3), Y(4), 10, 1, h); s.r(X(5), Y(2), 6, 2, h); s.r(X(6), Y(0), 4, 2, h); s.r(X(7), Y(-1), 3, 1, h)
        s.r(X(9), Y(-2), 2, 1, h); s.p(X(7), Y(3), C["trim"])
    if C.get("helm"):
        h = C["helm"]
        s.r(X(4), Y(3), 8, 2, h); s.r(X(4), Y(5), 1, 4, h); s.r(X(11), Y(5), 1, 4, h); s.r(X(7), Y(2), 2, 1, "#a33a2e")
        s.r(X(7), Y(5), 2, 3, h)  # nasal guard
    if C.get("goggles"):
        s.r(X(4), Y(5), 8, 1, "#4a3a2a"); s.r(X(5), Y(5), 2, 1, "#f2b64a"); s.r(X(9), Y(5), 2, 1, "#f2b64a")
    if C.get("hood"):
        h = C["hood"]
        s.r(X(4), Y(3), 8, 2, h); s.r(X(4), Y(5), 1, 6, h); s.r(X(11), Y(5), 1, 6, h); s.r(X(5), Y(9), 6, 2, C["trim"])  # mask
    if C.get("cowl"):
        h = C["cowl"]
        s.r(X(4), Y(3), 8, 2, h); s.r(X(4), Y(5), 1, 5, h); s.r(X(11), Y(5), 1, 5, h); s.p(X(7), Y(3), C["trim"]); s.p(X(8), Y(3), C["trim"])
    if C.get("cap"):
        s.r(X(4), Y(3), 8, 2, C["cap"]); s.r(X(11), Y(4), 2, 1, C["cap"]); s.r(X(4), Y(1), 1, 3, "#c8402e"); s.p(X(3), Y(0), "#c8402e")
    s.outline()
    return s


ITEMS = {}


def item(name, draw, w=8, h=16):
    s = Px(w, h)
    draw(s)
    s.outline()
    s.svg("item-" + name)


def staff(s):
    s.r(3, 4, 1, 12, "#7a4e2a"); s.r(2, 1, 3, 3, "#9b7bff"); s.p(3, 2, "#e6dcff"); s.p(1, 2, "#6a4fd0"); s.p(5, 2, "#6a4fd0")
def hammer(s):
    s.r(3, 5, 1, 11, "#7a4e2a"); s.r(1, 2, 6, 3, "#8a94a2"); s.r(1, 2, 6, 1, "#c7ced8")
def wrench(s):
    s.r(3, 6, 2, 9, "#8a94a2"); s.r(2, 3, 4, 3, "#8a94a2"); s.r(3, 2, 2, 2, None); s.p(3, 3, None); s.p(4, 3, None); s.r(3, 15, 2, 1, "#6b7380")
def dagger(s):
    s.r(3, 4, 2, 7, "#d8dee6"); s.p(3, 3, "#d8dee6"); s.r(2, 11, 4, 1, "#d9a93a"); s.r(3, 12, 2, 3, "#5a3b22")
def holy(s):
    s.r(3, 6, 1, 10, "#d9a93a"); s.r(1, 1, 5, 5, "#f2d36b"); s.r(2, 2, 3, 3, "#fff3c4"); s.p(3, 0, "#f2d36b"); s.p(0, 3, "#f2d36b"); s.p(6, 3, "#f2d36b")
def bow(s):
    for y, x in enumerate([5, 4, 3, 3, 2, 2, 2, 2, 2, 2, 2, 3, 3, 4, 5]):
        s.p(x, y, "#8a5a2b")
    s.r(5, 0, 1, 15, "#e9e3d0")


def sparkle(s):
    c = "#fff3c4"
    s.p(2, 0, c); s.p(2, 4, c); s.p(0, 2, c); s.p(4, 2, c); s.p(2, 1, "#c9b6ff"); s.p(2, 3, "#c9b6ff"); s.p(1, 2, "#c9b6ff"); s.p(3, 2, "#c9b6ff"); s.p(2, 2, "#ffffff")


def mark_excl():
    s = Px(7, 14)
    s.r(2, 1, 3, 8, "#ffd23f"); s.r(2, 1, 1, 8, "#fff1a6"); s.r(2, 10, 3, 3, "#ffd23f")
    s.outline(); s.svg("mark-quete")


def mark_q():
    s = Px(9, 14)
    s.r(2, 1, 5, 2, "#ffd23f"); s.r(6, 2, 2, 3, "#ffd23f"); s.r(4, 5, 3, 2, "#ffd23f"); s.r(4, 7, 2, 2, "#ffd23f"); s.r(4, 10, 2, 2, "#ffd23f")
    s.r(1, 2, 2, 2, "#ffd23f"); s.r(2, 1, 5, 1, "#fff1a6")
    s.outline(); s.svg("mark-rendu")


def glow():
    s = Px(24, 10)
    for y in range(10):
        for x in range(24):
            dx, dy = (x - 11.5) / 12, (y - 5) / 5
            d = dx * dx + dy * dy
            if d < 1:
                a = int((1 - d) * 150)
                s.p(x, y, "#ffd86b%02x" % a)
    s.svg("halo")


def zzz():
    s = Px(5, 5); s.r(0, 0, 5, 1, "#e9e3d0"); s.p(3, 1, "#e9e3d0"); s.p(2, 2, "#e9e3d0"); s.p(1, 3, "#e9e3d0"); s.r(0, 4, 5, 1, "#e9e3d0"); s.svg("z")


def flame(name, shape):
    s = Px(5, 8)
    cols = {"o": "#ff9b2f", "y": "#ffe27a", "r": "#e2461f"}
    for y, row in enumerate(shape):
        for x, ch in enumerate(row):
            if ch in cols:
                s.p(x, y, cols[ch])
    s.svg(name)


# ---------------------------------------------------------------- buildings
STONE, STONE2, STONE3 = "#8d8a93", "#74717c", "#a6a3ab"
WOOD, WOOD2, WOODD = "#8a5a2b", "#6b4422", "#4a2e17"
PLASTER = "#e7d8b4"
DARKWIN = "#2a2433"
LIGHT = "#ffcf5a"


class Building:
    def __init__(s, name, w, h):
        s.name, s.w, s.h = name, w, h
        s.px = Px(w, h)
        s.lights = Px(w, h)

    def bricks(s, x, y, w, h, a=STONE, b=STONE2, c=STONE3):
        s.px.r(x, y, w, h, a)
        for j in range(y, y + h):
            if (j - y) % 3 == 2:
                s.px.r(x, j, w, 1, b)
            else:
                off = 0 if ((j - y) // 3) % 2 == 0 else 3
                for i in range(x + off, x + w, 6):
                    s.px.p(i, j, b)
        for i in range(x + 1, x + w, 7):
            s.px.p(i, y + 1, c)

    def planks(s, x, y, w, h, a=WOOD, b=WOOD2):
        s.px.r(x, y, w, h, a)
        for i in range(x, x + w, 3):
            s.px.r(i, y, 1, h, b)

    def roof(s, x, y, w, h, a, b, overhang=2):
        # stepped gable: each row narrower towards the top
        for j in range(h):
            inset = int((h - 1 - j) * (w / 2) / h)
            s.px.r(x - overhang + inset, y + j, w + 2 * overhang - 2 * inset, 1, a if j % 2 == 0 else b)

    def window(s, x, y, w=4, h=4, frame=WOODD, arch=False, light=LIGHT):
        s.px.r(x - 1, y - 1, w + 2, h + 2, frame)
        s.px.r(x, y, w, h, DARKWIN)
        s.lights.r(x, y, w, h, light)
        if w >= 4:
            s.px.r(x + w // 2, y, 1, h, frame); s.lights.r(x + w // 2, y, 1, h, None)
        if arch:
            s.px.p(x - 1, y - 1, None); s.px.p(x + w, y - 1, None)

    def door(s, x, y, w=5, h=7):
        s.px.r(x - 1, y - 1, w + 2, h + 1, WOODD)
        s.px.r(x, y, w, h, WOOD2)
        s.px.r(x + w - 2, y + h // 2, 1, 1, "#d9a93a")

    def save(s):
        s.px.outline()
        s.px.svg("bat-" + s.name)
        s.lights.svg("bat-" + s.name + "-nuit")


def tour():
    b = Building("tour", 28, 58)
    b.bricks(5, 22, 18, 36, "#7f7a8c", "#655f73", "#9a95a6")
    # conical roof
    for j in range(20):
        half = 1 + j * 11 // 19
        b.px.r(14 - half, 2 + j, 2 * half, 1, "#5b3a9c" if (j // 2) % 2 == 0 else "#4a2f86")
    b.px.r(3, 22, 22, 2, "#41286f")
    b.px.r(13, 0, 2, 3, "#e8c35a"); b.px.p(12, 1, "#e8c35a"); b.px.p(15, 1, "#e8c35a")
    b.window(12, 27, 4, 5, arch=True, light="#c9a8ff")
    b.window(12, 37, 4, 5, arch=True, light="#c9a8ff")
    b.window(8, 32, 2, 3, light="#c9a8ff"); b.window(18, 32, 2, 3, light="#c9a8ff")
    b.door(11, 50, 6, 8)
    b.px.r(9, 46, 10, 1, "#e8c35a")
    b.save()


def atelier():
    b = Building("atelier", 40, 38)
    b.bricks(2, 16, 36, 22, "#9c5a3c", "#7a4430", "#b36c4a")
    b.roof(2, 4, 36, 12, "#4a4f5c", "#3b3f4a")
    b.px.r(28, 0, 5, 9, "#6b4a3a"); b.px.r(28, 0, 5, 1, "#3b2a22")
    b.window(6, 21, 8, 5); b.window(26, 21, 8, 5)
    b.door(17, 29, 6, 9)
    # gear sign
    for (x, y) in [(19, 9), (20, 9), (18, 10), (21, 10), (17, 11), (22, 11), (18, 12), (21, 12), (19, 13), (20, 13)]:
        b.px.p(x, y, "#e8c35a")
    b.px.r(19, 11, 2, 1, "#e8c35a"); b.px.r(19, 8, 2, 1, "#e8c35a"); b.px.r(16, 11, 1, 1, "#e8c35a"); b.px.r(23, 11, 1, 1, "#e8c35a"); b.px.r(19, 14, 2, 1, "#e8c35a")
    b.save()


def forge():
    b = Building("forge", 46, 36)
    b.bricks(2, 14, 42, 22)
    b.roof(2, 4, 42, 10, "#5b5f6b", "#474a55")
    b.px.r(34, 0, 6, 10, "#74717c"); b.px.r(34, 0, 6, 1, "#3b3f4a")
    # open front
    b.px.r(8, 20, 22, 16, "#2a1d1a"); b.px.r(7, 19, 24, 1, WOODD); b.px.r(7, 19, 1, 17, WOODD); b.px.r(30, 19, 1, 17, WOODD)
    b.px.r(10, 26, 8, 6, "#5a2a1a")
    b.lights.r(11, 27, 6, 4, "#ff8a2a"); b.lights.r(12, 28, 4, 2, "#ffd36b")
    b.window(35, 22, 4, 4, light="#ff9b3f")
    b.save()
    s = Px(12, 7)
    s.r(0, 0, 12, 2, "#5a5f6b"); s.r(0, 0, 12, 1, "#8a8f9b"); s.r(3, 2, 6, 2, "#4a4f5a"); s.r(2, 4, 8, 2, "#3b3f4a")
    s.outline(); s.svg("enclume")


def taverne():
    b = Building("taverne", 50, 46)
    b.px.r(3, 18, 44, 28, PLASTER)
    for x in (3, 14, 25, 36, 46):
        b.px.r(x, 18, 1, 28, WOODD)
    b.px.r(3, 18, 44, 1, WOODD); b.px.r(3, 31, 44, 1, WOODD); b.px.r(3, 45, 44, 1, WOODD)
    for x in (4, 15, 26, 37):
        for k in range(10):
            b.px.p(x + k, 19 + int(k * 1.2), WOOD2)
    b.roof(3, 2, 44, 16, "#a3442e", "#86361f")
    b.px.r(38, 0, 5, 8, STONE2)
    b.window(7, 35, 4, 4); b.window(30, 35, 4, 4); b.window(40, 35, 4, 4)
    b.window(8, 22, 4, 4); b.window(30, 22, 4, 4); b.window(40, 22, 4, 4)
    b.door(19, 37, 6, 9)
    # hanging sign with a mug
    b.px.r(17, 27, 11, 1, WOODD); b.px.r(18, 28, 1, 1, WOODD); b.px.r(26, 28, 1, 1, WOODD)
    b.px.r(17, 29, 11, 6, "#c98b52"); b.px.r(20, 30, 4, 4, "#e8c35a"); b.px.r(20, 30, 4, 1, "#fbf6e8"); b.px.r(24, 31, 1, 2, "#e8c35a")
    b.save()
    s = Px(26, 6)
    s.r(0, 0, 26, 2, WOOD); s.r(0, 0, 26, 1, "#a8693a"); s.r(2, 2, 2, 4, WOODD); s.r(22, 2, 2, 4, WOODD)
    s.outline(); s.svg("banc")
    s = Px(6, 6); s.r(1, 1, 3, 4, "#e8c35a"); s.r(1, 1, 3, 1, "#fbf6e8"); s.r(4, 2, 1, 2, "#e8c35a"); s.outline(); s.svg("chope")


def alchimiste():
    b = Building("alchimiste", 38, 38)
    b.planks(2, 14, 34, 24, "#5d6b3f", "#4a5632")
    b.roof(2, 2, 34, 12, "#3f6b5a", "#33584a")
    # awning
    for i in range(0, 34, 4):
        b.px.r(2 + i, 22, 2, 3, "#d9a93a"); b.px.r(4 + i, 22, 2, 3, "#2f6b4a")
    b.px.r(2, 25, 34, 1, "#2f6b4a")
    b.px.r(5, 27, 16, 9, DARKWIN); b.lights.r(5, 27, 16, 9, "#7fe0a0")
    for i, c in enumerate(["#c8402e", "#7a5ad0", "#3fb6a0", "#e8c35a", "#d499c9"]):
        b.px.r(6 + i * 3, 31, 2, 4, c); b.px.p(6 + i * 3, 30, "#e9e3d0")
    b.px.r(5, 30, 16, 1, WOODD)
    b.door(25, 28, 6, 10)
    b.window(16, 16, 5, 4, light="#9bf0b8")
    b.save()


def guilde():
    b = Building("guilde", 32, 38)
    b.planks(2, 16, 28, 22, "#3a3036", "#2c2429")
    for j in range(14):
        inset = int((13 - j) * 15 / 14)
        b.px.r(0 + inset + (1 if j < 6 else 0), 2 + j, 32 - 2 * inset, 1, "#2f3a33" if j % 2 else "#26302a")
    b.window(6, 21, 3, 3, light="#c86a5a")
    b.door(15, 28, 6, 10)
    # hooded figure sign
    b.px.r(22, 19, 6, 7, "#1d1a22"); b.px.r(23, 20, 4, 4, "#7a1f2b"); b.px.p(24, 22, "#d8dee6"); b.px.p(25, 22, "#d8dee6")
    b.save()


def temple():
    b = Building("temple", 48, 52)
    b.bricks(4, 22, 40, 30, "#d8d2c2", "#b8b1a0", "#ece7da")
    b.roof(4, 10, 40, 12, "#c9c0a6", "#b8af96", overhang=3)
    b.px.r(1, 22, 46, 2, "#b8af96")
    for x in (7, 15, 31, 39):
        b.px.r(x, 24, 3, 26, "#f0ebde"); b.px.r(x + 2, 24, 1, 26, "#c9c0a6")
    b.px.r(2, 50, 44, 2, "#b8b1a0")
    # bell tower
    b.px.r(20, 0, 8, 12, "#d8d2c2"); b.px.r(21, 3, 6, 5, "#3a3036"); b.px.r(23, 4, 2, 3, "#d9a93a"); b.px.r(19, 0, 10, 1, "#b8af96")
    # sun disc
    b.px.r(21, 14, 6, 5, "#e8c35a"); b.px.r(22, 15, 4, 3, "#fff3c4")
    b.door(21, 40, 6, 10)
    b.window(22, 27, 4, 7, arch=True, light="#ffe9a0")
    b.save()


def ecurie():
    b = Building("ecurie", 44, 34)
    b.planks(2, 12, 40, 22, "#9a3b2a", "#7f2f21")
    b.roof(2, 2, 40, 10, "#5a3b22", "#4a2e17")
    b.px.r(14, 18, 16, 16, "#e9e3d0")
    b.px.r(15, 19, 14, 15, "#7f2f21")
    for k in range(14):
        b.px.p(15 + k, 19 + k, "#e9e3d0"); b.px.p(28 - k, 19 + k, "#e9e3d0")
    b.window(5, 17, 4, 3); b.window(35, 17, 4, 3)
    b.px.r(19, 6, 6, 4, "#e9c35a"); b.px.r(19, 6, 6, 1, "#c9a03a")  # hay loft
    b.save()
    s = Px(14, 9)
    s.r(0, 2, 14, 7, "#e8c25a"); s.r(0, 2, 14, 1, "#f5da7a"); s.r(0, 5, 14, 1, "#c9a03a"); s.r(4, 0, 6, 2, "#e8c25a")
    s.outline(); s.svg("foin")
    # a horse head peeking out
    s = Px(12, 10)
    s.r(2, 2, 7, 4, "#8a5a2b"); s.r(7, 3, 4, 4, "#8a5a2b"); s.r(3, 1, 2, 1, "#8a5a2b"); s.r(2, 0, 1, 2, "#4a2e17"); s.r(1, 2, 2, 6, "#4a2e17"); s.p(8, 4, "#1d1a22")
    s.r(2, 6, 5, 4, "#8a5a2b")
    s.outline(); s.svg("cheval")


def fontaine():
    s = Px(26, 22)
    s.r(1, 12, 24, 8, "#8d8a93"); s.r(1, 12, 24, 1, "#b0adb6"); s.r(1, 19, 24, 1, "#625f69")
    for i in range(3, 24, 5):
        s.r(i, 13, 1, 6, "#74717c")
    s.r(11, 2, 4, 10, "#8d8a93"); s.r(9, 1, 8, 2, "#a6a3ab"); s.r(11, 0, 4, 1, "#b0adb6")
    s.outline(); s.svg("fontaine")


def lampadaire():
    s = Px(8, 34)
    s.r(3, 8, 2, 26, "#3b3542"); s.r(1, 3, 6, 6, "#3b3542"); s.r(2, 4, 4, 4, "#5a4a3a"); s.r(0, 2, 8, 1, "#3b3542"); s.r(1, 32, 6, 2, "#3b3542")
    s.svg("lampadaire")
    s = Px(8, 34); s.r(2, 4, 4, 4, "#ffd36b"); s.svg("lampadaire-nuit")


def sapin(name, h):
    s = Px(16, h)
    for j in range(h - 4):
        half = 1 + (j % 6) + j // 6
        half = min(half, 7)
        s.r(8 - half, j, 2 * half, 1, "#2f5f3a" if j % 3 else "#3d7548")
    s.r(7, h - 4, 2, 4, "#4a2e17")
    s.outline(); s.svg(name)


def banner_shape():
    # district pennant (tinted with the text color)
    s = Px(10, 14)
    s.r(0, 0, 10, 11, "#ffffff"); s.r(0, 11, 4, 1, "#ffffff"); s.r(6, 11, 4, 1, "#ffffff"); s.r(0, 12, 3, 1, "#ffffff"); s.r(7, 12, 3, 1, "#ffffff"); s.r(0, 13, 2, 1, "#ffffff"); s.r(8, 13, 2, 1, "#ffffff")
    s.svg("fanion")


def charges():
    # heraldic charges, white (tinted)
    W = "#ffffff"
    defs = {
        "etoile": ["...#...", "...#...", "#######", ".#####.", "..###..", ".##.##.", "##...##"],
        "lune": ["..###..", ".##....", "##.....", "##.....", "##.....", ".##....", "..###.."],
        "tour": ["#.#.#.#", "#######", ".#####.", ".##.##.", ".#####.", ".#####.", "#######"],
        "cle": [".###...", "#...#..", ".###...", "..#....", "..###..", "..#....", "..##..."],
        "chene": ["..###..", ".#####.", "#######", ".#####.", "...#...", "...#...", "..###.."],
        "coupe": ["#######", "#######", ".#####.", "..###..", "...#...", "...#...", ".#####."],
        "epee": ["...#...", "...#...", "...#...", "...#...", ".#####.", "...#...", "...#..."],
        "soleil": ["#..#..#", ".#####.", ".##.##.", "###.###", ".##.##.", ".#####.", "#..#..#"],
    }
    for k, rows in defs.items():
        s = Px(7, 7)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == "#":
                    s.p(x, y, W)
        s.svg("blason-" + k)


def icons():
    # small UI glyphs (tinted): split right, split down, zoom, close, plus, scroll
    W = "#ffffff"
    defs = {
        "split-r": ["#########", "#...#...#", "#...#...#", "#...#...#", "#...#...#", "#...#...#", "#########"],
        "split-d": ["#########", "#.......#", "#.......#", "#########", "#.......#", "#.......#", "#########"],
        "zoom": ["###...###", "#.......#", "#.......#", ".........", "#.......#", "#.......#", "###...###"],
        "close": ["##.....##", ".##...##.", "..##.##..", "...###...", "..##.##..", ".##...##.", "##.....##"],
        "plus": ["....#....", "....#....", "....#....", "#########", "....#....", "....#....", "....#...."],
        "epee": ["........#", ".......#.", "......#..", "#...##...", ".#.##....", "..##.....", ".#.#....."],
        "parchemin": [".#######.", "#.......#", ".#.###.#.", ".#.....#.", ".#.###.#.", "#.......#", ".#######."],
    }
    for k, rows in defs.items():
        s = Px(9, 7)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == "#":
                    s.p(x, y, W)
        s.svg("ic-" + k)


def crest():
    # Valbrume's crest: a lantern on a shield
    s = Px(16, 18)
    s.r(1, 0, 14, 12, "#2f4a7a"); s.r(2, 12, 12, 2, "#2f4a7a"); s.r(4, 14, 8, 2, "#2f4a7a"); s.r(6, 16, 4, 1, "#2f4a7a")
    s.r(8, 0, 7, 12, "#7a1f2b"); s.r(8, 12, 6, 2, "#7a1f2b"); s.r(8, 14, 4, 2, "#7a1f2b"); s.r(8, 16, 2, 1, "#7a1f2b")
    s.r(6, 3, 4, 1, "#e8c35a"); s.r(5, 4, 6, 6, "#e8c35a"); s.r(6, 5, 4, 4, "#ffe9a0"); s.r(7, 6, 2, 2, "#ff9b2f"); s.r(5, 10, 6, 1, "#c99a3a"); s.r(7, 2, 2, 1, "#e8c35a")
    s.outline("#e8c35a"); s.svg("blason-valbrume")


def paves():
    import random
    rnd = random.Random(7)
    s = Px(64, 22)
    s.r(0, 0, 64, 22, "#45414d")
    y = 0
    row = 0
    while y < 22:
        h = 4 if row % 2 == 0 else 5
        x = -rnd.randint(0, 5)
        while x < 64:
            w = rnd.randint(5, 9)
            c = rnd.choice(["#5d5866", "#625d6b", "#57525f", "#6a6473"])
            s.r(max(0, x), y, min(w - 1, 64 - max(0, x)) if x >= 0 else w - 1 + x, h - 1, c)
            if x >= 0:
                s.r(x, y, w - 1, 1, "#77717f")
            x += w
        y += h
        row += 1
    s.svg("paves")


if __name__ == "__main__":
    for race in RACES:
        for cls in CLASSES:
            hero(race, cls).svg(f"h-{race}-{cls}")
            hero(race, cls, sit=True).svg(f"h-{race}-{cls}-assis")
    item("baton", staff); item("marteau", hammer); item("cle", wrench); item("dague", dagger); item("relique", holy); item("arc", bow)
    s = Px(5, 5); sparkle(s); s.svg("etincelle")
    mark_excl(); mark_q(); glow(); zzz()
    flame("flamme-a", ["..y..", ".yo..", ".yoo.", "oyyo.", "oyyoo", "royor", ".ror.", "..r.."])
    flame("flamme-b", [".y...", "..y..", ".oyo.", ".oyyo", "ooyyo", "royyr", ".rorr", "..r.."])
    tour(); atelier(); forge(); taverne(); alchimiste(); guilde(); temple(); ecurie(); fontaine(); lampadaire()
    paves(); sapin("sapin", 30); banner_shape(); charges(); icons(); crest()
    print(len(os.listdir(OUT)), "files in", OUT)
