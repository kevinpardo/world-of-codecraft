import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import Px
def from_rows(name, rows, pal):
    s = Px(len(rows[0]), len(rows))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in pal: s.p(x, y, pal[ch])
    s.outline(); s.svg(name)
from_rows("res-or", [
 "............",
 "....yyyy....",
 "...yYYYYy...",
 "...yyyyyy...",
 ".yyyyoyyyy..",
 "yYYYYyYYYYy.",
 "yyyyyyyyyyy.",
 "yoyyyoyyoyy.",
 "yyyyyyyyyyy.",
 ".oooooooooo.",
], {"y": "#e8c35a", "Y": "#fff1a6", "o": "#b8862a"})
from_rows("res-bois", [
 "............",
 "...bbbbbbb..",
 "..rRbbbbbbb.",
 "..RrRbbbbbb.",
 "..rRbbbbbbb.",
 "bbbbbbbbb...",
 "rRbbbbbbbbb.",
 "RrRbbbbbbbb.",
 "rRbbbbbbbbb.",
 ".dddddddddd.",
], {"b": "#8a5a2b", "r": "#c98b52", "R": "#e0b07a", "d": "#5a3a1e"})
from_rows("res-heros", [
 "....hhhh....",
 "...hhhhhh...",
 "...hssssh...",
 "...sesses...",
 "...ssssss...",
 "....ssss....",
 "..cccccccc..",
 ".cccccccccc.",
 ".cccccccccc.",
 ".cccccccccc.",
], {"h": "#9aa4b1", "s": "#e8b48a", "e": "#1d1a22", "c": "#2f4a7a"})
from_rows("res-sablier", [
 ".wwwwwwww.",
 "..g....g..",
 "..gyyyyg..",
 "...gyyg...",
 "....gg....",
 "....gg....",
 "...g..g...",
 "..g.yy.g..",
 "..gyyyyg..",
 ".wwwwwwww.",
], {"w": "#8a5a2b", "g": "#cfe6f2", "y": "#e8c35a"})
s = Px(5, 3); s.r(0,0,5,3,"#ffffff"); s.svg("blanc")
print("ok")
