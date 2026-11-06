"""Gera imagens sinteticas das duas marcas (Bioma e OTIUM) com area protegida marcada.

As imagens imitam as proporcoes reais do caso Bioma (fachada 4050x1992, piscina 7200x4234,
living 2048x928) em resolucao reduzida. A area protegida (predio, piscina, sofa) e o que
nao pode ser cortado nem inventado no desdobramento.
"""
import json, os, random
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")
random.seed(7)


def grad(w, h, top, bottom):
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        d.line([(0, y), (w, y)], fill=c)
    return im


def trees(d, w, y0, h, color, n=40):
    for _ in range(n):
        x = random.randint(-20, w)
        r = random.randint(int(h * 0.3), int(h * 0.7))
        d.ellipse([x - r, y0 - r // 2, x + r, y0 + r], fill=color)


def tower(d, x, y, w, h, body, win, rows, cols):
    d.rectangle([x, y, x + w, y + h], fill=body)
    mw, mh = w / (cols * 2 + 1), h / (rows * 2 + 1)
    for r in range(rows):
        for c in range(cols):
            wx = x + mw * (2 * c + 1)
            wy = y + mh * (2 * r + 1)
            d.rectangle([wx, wy, wx + mw, wy + mh * 0.9], fill=win)


def fachada(name, w, h, sky, body, win, ground, tx):
    im = grad(w, h, sky[0], sky[1])
    d = ImageDraw.Draw(im)
    # duas torres na regiao [tx, tx+0.3]
    bx = int(w * tx); bw = int(w * 0.12)
    t1 = (bx, int(h * 0.12), bw, int(h * 0.70))
    t2 = (bx + int(bw * 1.25), int(h * 0.22), bw, int(h * 0.60))
    tower(d, *t1, body, win, 18, 5)
    tower(d, *t2, body, win, 15, 5)
    d.rectangle([0, int(h * 0.80), w, h], fill=ground)
    trees(d, w, int(h * 0.82), int(h * 0.12), (46, 82, 52), 60)
    x0 = t1[0]; x1 = t2[0] + t2[2]
    prot = [x0 / w, 0.12, (x1 - x0) / w, 0.70]
    return im, prot


def piscina(name, w, h, sky, water, deck, body, win):
    im = grad(w, h, sky[0], sky[1])
    d = ImageDraw.Draw(im)
    tower(d, int(w * 0.55), int(h * 0.05), int(w * 0.10), int(h * 0.45), body, win, 12, 4)
    trees(d, w, int(h * 0.50), int(h * 0.10), (56, 96, 60), 50)
    d.rectangle([0, int(h * 0.52), w, h], fill=deck)
    d.polygon([(w * 0.10, h * 0.62), (w * 0.90, h * 0.62), (w * 0.97, h * 0.92), (w * 0.03, h * 0.92)], fill=water)
    for i in range(30):
        y = h * 0.64 + i * h * 0.009
        d.line([(w * 0.12, y), (w * 0.88, y)], fill=tuple(min(255, c + 25) for c in water), width=1)
    prot = [0.03, 0.05, 0.94, 0.87]  # piscina + torre: precisa aparecer quase toda
    # area minima que precisa ficar visivel: a piscina
    core = [0.10, 0.60, 0.80, 0.32]
    return im, core


def living(name, w, h, wall, floor, sofa):
    im = Image.new("RGB", (w, h), wall)
    d = ImageDraw.Draw(im)
    d.rectangle([0, int(h * 0.70), w, h], fill=floor)
    d.rectangle([int(w * 0.62), int(h * 0.12), int(w * 0.95), int(h * 0.62)], fill=(200, 220, 235))  # janela
    d.rounded_rectangle([int(w * 0.20), int(h * 0.48), int(w * 0.58), int(h * 0.80)], 18, fill=sofa)
    d.ellipse([int(w * 0.30), int(h * 0.80), int(w * 0.48), int(h * 0.90)], fill=(120, 90, 60))
    prot = [0.20, 0.48, 0.38, 0.42]
    return im, prot


def icon(name, kind, color, bg):
    s = 240
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([4, 4, s - 4, s - 4], fill=bg)
    if kind == "solar":
        d.ellipse([80, 60, 160, 140], fill=color)
        for i in range(8):
            import math
            a = i * math.pi / 4
            d.line([(120 + 55 * math.cos(a), 100 + 55 * math.sin(a)), (120 + 75 * math.cos(a), 100 + 75 * math.sin(a))], fill=color, width=8)
        d.polygon([(60, 190), (180, 190), (165, 160), (75, 160)], fill=color)
    elif kind == "chuva":
        d.ellipse([60, 60, 180, 130], fill=color)
        for x in (80, 120, 160):
            d.line([(x, 145), (x - 12, 190)], fill=color, width=10)
    else:  # coleta
        d.rectangle([75, 90, 165, 195], fill=color)
        d.rectangle([65, 70, 175, 88], fill=color)
        d.rectangle([105, 55, 135, 70], fill=color)
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = {}

    def save(aid, im, prot, kind="photo", real=None):
        fn = aid + ".png"
        im.save(os.path.join(OUT, fn))
        manifest[aid] = {"file": fn, "width": im.width, "height": im.height,
                         "protected": prot, "kind": kind, "real_size": real}

    # BIOMA (verdes, creme)
    im, p = fachada("b", 2025, 996, ((168, 196, 214), (236, 226, 204)), (222, 214, 196), (70, 90, 96), (110, 140, 98), 0.52)
    save("bioma_fachada", im, p, real=[4050, 1992])
    im, p = piscina("b", 1800, 1058, ((150, 190, 215), (230, 224, 210)), (64, 150, 180), (214, 200, 176), (230, 222, 205), (80, 100, 105))
    save("bioma_piscina", im, p, real=[7200, 4234])
    im, p = living("b", 1024, 464, (232, 224, 210), (170, 140, 110), (88, 110, 92))
    save("bioma_living", im, p, real=[2048, 928])
    for k in ("solar", "chuva", "coleta"):
        save("bioma_icon_" + k, icon(k, k, (30, 62, 46, 255), (226, 218, 196, 255)), [0, 0, 1, 1], kind="icon")

    # OTIUM (terracota, grafite)
    im, p = fachada("o", 1800, 1000, ((120, 130, 150), (226, 196, 170)), (60, 58, 62), (210, 170, 120), (120, 110, 90), 0.30)
    save("otium_fachada", im, p, real=[1800, 1000])
    im, p = piscina("o", 1600, 900, ((200, 170, 150), (240, 220, 200)), (90, 120, 130), (170, 120, 96), (60, 58, 62), (210, 170, 120))
    save("otium_spa", im, p, real=[1600, 900])
    im, p = living("o", 1200, 520, (236, 228, 220), (120, 92, 72), (180, 110, 80))
    save("otium_living", im, p, real=[1200, 520])

    json.dump(manifest, open(os.path.join(OUT, "assets.json"), "w"), indent=1)
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
