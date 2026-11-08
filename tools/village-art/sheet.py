import os
from PIL import Image, ImageDraw, ImageFont
F = os.path.expanduser('~/.config/herdr-app/mods/village-bourg/fonts/')
fl = ImageFont.truetype(F + 'Jersey15-Regular.ttf', 26)
fh = ImageFont.truetype(F + 'Jacquard24-Regular.ttf', 48)
A = 'assets/'
BG = (60, 63, 72); TX = (226, 220, 205); HD = (232, 195, 90)

def comp(n):
    im = Image.open(A + n + '.png').convert('RGBA')
    if os.path.exists(A + n + '-shadow.png'):
        s = Image.open(A + n + '-shadow.png').convert('RGBA')
        base = Image.new('RGBA', s.size, (0, 0, 0, 0)); base.alpha_composite(s); base.alpha_composite(im); return base
    return im

H6 = [('elf', 'mage'), ('orc', 'warrior'), ('human', 'priest'), ('undead', 'rogue'), ('dwarf', 'artificer'), ('human', 'ranger'),
      ('human', 'warrior'), ('orc', 'rogue'), ('elf', 'ranger')]
sections = [
    ('Buildings (2x, soft shadow + contact AO layer under; S=1.4)', [(f'b-{n}', n) for n in ('townhall', 'magetower', 'forge', 'barracks', 'temple', 'tavern', 'barn')]),
    ('Small buildings & props', [(f'b-{n}', n) for n in ('stall-red', 'stall-blue', 'stall-green', 'well', 'noticeboard', 'campfire', 'fence-x', 'fence-y', 'rocks', 'bush', 'tree-oak', 'tree-pine', 'tree-autumn')]),
    ('Ground tiles 64x32 logical (seamless)', [(f't-{n}', n) for n in ('grass', 'grass-flowers', 'dirt', 'paved', 'water', 'crop')]),
    ('Heroes: stand / work / sit', [(f'h-{r}-{c}-{p}', f'{r} {c} {p}') for (r, c) in H6 for p in ('stand', 'work', 'sit')]),
    ('States, icons, UI', [('m-blocked', '! blocked'), ('m-done', '? done'), ('ring-selected', 'selected'), ('ring-blocked', 'blocked ring'), ('ring-done', 'done halo'),
                           ('icon-gold', 'gold'), ('icon-wood', 'wood'), ('ui-panel', 'panel + header')]),
]
W = 4200
rows = []
y = 20
canvas = Image.new('RGBA', (W, 8000), BG + (255,))
d = ImageDraw.Draw(canvas); d.fontmode = '1'
d.text((30, y), 'Valbrume - direction A v2 : pixel art HD + global light (1 art px = 1 logical px, shown at 2x)', font=fh, fill=HD); y += 80
for title, items in sections:
    d.text((30, y), title, font=fh, fill=HD); y += 64
    x = 30; rowh = 0
    for (n, label) in items:
        im = comp(n)
        w, h = im.size
        if x + max(w, int(d.textlength(label, font=fl))) > W - 30:
            x = 30; y += rowh + 50; rowh = 0
        canvas.alpha_composite(im, (x, y))
        d.text((x, y + h + 6), label, font=fl, fill=TX)
        x += max(w, int(d.textlength(label, font=fl))) + 36; rowh = max(rowh, h)
    y += rowh + 60
canvas = canvas.crop((0, 0, W, y + 10))
canvas.convert('RGB').save('sheet.png')
# roster of all 30 race x class combos (standing)
ims = [Image.open(f'tmp/h2/h-{r}-{c}-stand.png').convert('RGBA') for r in ('human', 'elf', 'orc', 'undead', 'dwarf') for c in ('mage', 'warrior', 'priest', 'ranger', 'rogue', 'artificer')]
cw = max(i.size[0] for i in ims) + 20; ch = max(i.size[1] for i in ims) + 20
ro = Image.new('RGBA', (cw * 6 + 20, ch * 5 + 20), BG + (255,))
for k, im in enumerate(ims):
    ro.alpha_composite(im, (20 + (k % 6) * cw + (cw - im.size[0]) // 2, 20 + (k // 6) * ch + (ch - im.size[1])))
ro.convert('RGB').save('roster-30.png')
print(canvas.size)
