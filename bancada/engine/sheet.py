"""Prancha de contato: uma linha por braco, uma coluna por formato. Uso: sheet.py run layout out.png [bracos]"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
run, L, out = sys.argv[1], sys.argv[2], sys.argv[3]
base = os.path.join(ROOT, "runs", run)
arms = sys.argv[4].split(",") if len(sys.argv) > 4 else sorted(os.listdir(os.path.join(base, "renders")))
fmts = ["email_600x1200", "post_1080x1350", "card_1080x1080", "stories_1080x1920", "banner_970x250"]
CH = 420
cols = []
for f in fmts:
    w, h = map(int, f.split("_")[1].split("x"))
    s = CH / h if f != "banner_970x250" else 420 / w
    cols.append((f, int(w * s), int(h * s)))
Wt = sum(c[1] for c in cols) + 20 * (len(cols) + 1) + 90
Ht = (CH + 50) * len(arms) + 20
sheet = Image.new("RGB", (Wt, Ht), (235, 235, 235))
d = ImageDraw.Draw(sheet)
fnt = ImageFont.truetype(os.path.join(ROOT, "fonts", "Barlow-600.ttf"), 18)
for r, a in enumerate(arms):
    y = 20 + r * (CH + 50)
    d.text((10, y + CH // 2), a, fill=(0, 0, 0), font=fnt)
    x = 90
    for f, w, h in cols:
        p = os.path.join(base, "renders", a, f"{L}__{f}.png")
        if os.path.exists(p):
            sheet.paste(Image.open(p).convert("RGB").resize((w, h)), (x, y))
        cj = os.path.join(base, "checks", a, f"{L}__{f}.json")
        if os.path.exists(cj):
            c = json.load(open(cj))
            lab = ("OK " if c["eligible"] else f"FALHA {c['fails']} ") + f"{c['soft_score']:.2f}"
            d.text((x, y + h + 4), lab, fill=(0, 120, 0) if c["eligible"] else (180, 0, 0), font=fnt)
        x += w + 20
sheet.save(out)
