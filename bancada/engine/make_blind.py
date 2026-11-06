"""Monta o julgamento cego: para cada (peca, formato), embaralha os bracos e etiqueta por letra.

Uso: make_blind.py <run> <arquivo_chave_fora_do_repo> [bracos]
Gera runs/<run>/blind/<layout>/<formato>/sheet.png e <letra>.png. A chave (letra -> braco)
fica num arquivo separado que os jurados nao leem (Ato 1 da auditoria C-08: preferencia cega).
"""
import json, os, random, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
run, keyfile = sys.argv[1], sys.argv[2]
arms = sys.argv[3].split(",") if len(sys.argv) > 3 else ["A1", "B0", "R1", "R1opt", "T1", "R8", "R3", "R2"]
base = os.path.join(ROOT, "runs", run)
fmts = ["email_600x1200", "post_1080x1350", "card_1080x1080", "stories_1080x1920", "banner_970x250"]
layouts = sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, "fixtures")) if f.endswith(".json") and f != "formats.json")
fnt = ImageFont.truetype(os.path.join(ROOT, "fonts", "Barlow-600.ttf"), 34)
rng = random.Random(20261106)
key = {}
for L in layouts:
    for f in fmts:
        present = [a for a in arms if os.path.exists(os.path.join(base, "renders", a, f"{L}__{f}.png"))]
        rng.shuffle(present)
        letters = "ABCDEFGHIJ"[: len(present)]
        key[f"{L}__{f}"] = dict(zip(letters, present))
        out = os.path.join(base, "blind", L, f)
        os.makedirs(out, exist_ok=True)
        tiles = []
        for let, a in zip(letters, present):
            im = Image.open(os.path.join(base, "renders", a, f"{L}__{f}.png")).convert("RGB")
            im.save(os.path.join(out, let + ".png"))
            tiles.append((let, im))
        if not tiles:
            continue
        w, h = map(int, f.split("_")[1].split("x"))
        wide = w / h > 2
        cols = 2 if wide else 4
        tw = 900 if wide else 420
        th = int(tw * h / w)
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (tw + 30) + 30, rows * (th + 70) + 30), (225, 225, 225))
        d = ImageDraw.Draw(sheet)
        for i, (let, im) in enumerate(tiles):
            x = 30 + (i % cols) * (tw + 30)
            y = 30 + (i // cols) * (th + 70)
            d.text((x, y), let, fill=(0, 0, 0), font=fnt)
            sheet.paste(im.resize((tw, th)), (x, y + 44))
        sheet.save(os.path.join(out, "sheet.png"))
os.makedirs(os.path.dirname(keyfile), exist_ok=True)
json.dump(key, open(keyfile, "w"), indent=1)
print("pranchas:", sum(len(v) > 0 for v in key.values()), "chave:", keyfile)
