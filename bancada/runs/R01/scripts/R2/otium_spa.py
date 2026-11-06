#!/usr/bin/env python3
"""R2 — desdobramento de otium_spa para os 5 formatos.

Conceito da peça-mestra: foto full-bleed + faixa escura translúcida embaixo com
headline (esq.), logo (dir., na altura da headline) e CTA abaixo.
Formatos verticais: foto no topo (cover), faixa sobrepondo a base da foto e
descendo até o fim do canvas, bloco de texto na faixa com logo à direita.
Banner: foto inteira à esquerda, painel escuro (faixa) à direita com texto + logo.

Uso: python3 runs/R01/scripts/R2/otium_spa.py [--preview]
"""
import json, os, sys, copy
from PIL import Image, ImageFont, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
P = lambda *a: os.path.join(ROOT, *a)
SRC = json.load(open(P("fixtures", "otium_spa.json")))
FORMATS = json.load(open(P("fixtures", "formats.json")))
ASSETS = json.load(open(P("assets", "assets.json")))
OUT = P("runs", "R01", "candidates", "R2")
PREV = P("runs", "R01", "scripts", "R2", "preview")

FONT_FILES = {("Archivo", 700): "Archivo-700.ttf", ("Host Grotesk", 400): "HostGrotesk-400.ttf"}
_fc = {}


def font(name, weight, size):
    k = (name, weight, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(P("fonts", FONT_FILES[(name, weight)]), size)
    return _fc[k]


def em_metrics(st):
    f = font(st["font"], st["weight"], 1000)
    a, d = f.getmetrics()
    return a / 1000, d / 1000


def text_w(s, st):
    # mede em 1000px e escala (precisão sub-pixel)
    return font(st["font"], st["weight"], 1000).getlength(s) * st["size"] / 1000


def wrap(text, st, maxw):
    """quebra gulosa igual ao navegador (white-space: normal)."""
    words = text.split(" ")
    lines, cur = [], words[0]
    for w in words[1:]:
        if text_w(cur + " " + w, st) <= maxw:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def block(text, st, maxw):
    """retorna linhas, largura medida, altura medida (extensão dos glifos), offset do topo."""
    lines = wrap(text, st, maxw)
    a, d = em_metrics(st)
    ch = (a + d) * st["size"]
    L = st["line_height"] * st["size"]
    top = (L - ch) / 2
    h = (len(lines) - 1) * L + ch
    w = max(text_w(l, st) for l in lines)
    # robustez: a próxima palavra não pode caber por pouco (diferença de medição navegador x PIL)
    words = text.split(" ")
    return {"lines": lines, "w": w, "h": h, "top": top, "L": L, "ch": ch}


def fit_width(text, st, nlines):
    """menor largura que produz exatamente nlines linhas (quebra equilibrada) + folga."""
    total = text_w(text, st)
    lo, hi = 1.0, total + 2
    for _ in range(40):
        mid = (lo + hi) / 2
        if len(wrap(text, st, mid)) <= nlines:
            hi = mid
        else:
            lo = mid
    lines = wrap(text, st, hi)
    w = max(text_w(l, st) for l in lines)
    return w


def cover(asset, bw, bh, fx=0.55, fy=0.5):
    a = ASSETS[asset]
    arB, arI = bw / bh, a["width"] / a["height"]
    if arI > arB:
        ch, cw = 1.0, arB / arI
    else:
        cw, ch = 1.0, arI / arB
    cx = min(max(fx - cw / 2, 0), 1 - cw)
    cy = min(max(fy - ch / 2, 0), 1 - ch)
    return [round(cx, 5), round(cy, 5), round(cw, 5), round(ch, 5)]


def el(id_):
    return copy.deepcopy(next(e for e in SRC["elements"] if e["id"] == id_))


LOGO_AR = ASSETS["otium_logo"]["width"] / ASSETS["otium_logo"]["height"]


def text_el(id_, x, y, st_over, maxw, nlines=None):
    e = el(id_)
    e["style"].update(st_over)
    st = e["style"]
    if nlines:
        w = fit_width(e["text"], st, nlines)
    else:
        w = text_w(e["text"], st) if maxw is None else min(maxw, text_w(e["text"], st))
    # largura da caixa: largura medida + folga de 3% (não deixa o navegador quebrar diferente)
    bw = w * 1.03 + 4
    b = block(e["text"], st, bw)
    if nlines:
        assert len(b["lines"]) == nlines, (id_, b["lines"])
        # a próxima palavra não pode caber com folga dentro da caixa
    for i in range(len(b["lines"]) - 1):
        nxt = b["lines"][i + 1].split(" ")[0]
        assert text_w(b["lines"][i] + " " + nxt, st) > bw * 1.02, ("quebra frágil", id_, b["lines"])
    pad = 0.12 * st["size"] + 4
    bh = b["top"] + b["h"] + pad if b["top"] > 0 else b["h"] + pad
    e["geometry"].update({"x": round(x, 2), "y": round(y, 2), "width": round(bw, 2), "height": round(bh, 2)})
    # extensão medida esperada (para checagens locais)
    e["_m"] = {"x": x, "y": y + b["top"], "w": b["w"], "h": b["h"], "lines": b["lines"], "L": b["L"], "ch": b["ch"]}
    return e


def logo_el(x, y, w):
    e = el("logo")
    e["geometry"].update({"x": round(x, 2), "y": round(y, 2), "width": round(w, 2), "height": round(w / LOGO_AR, 2)})
    e["crop"] = [0, 0, 1, 1]
    return e


# ------------------------------------------------------------------ layouts
def vertical(fk, P_):
    F = FORMATS[fk]
    W, H = F["width"], F["height"]
    lx = P_["left"]
    rx = W - lx
    hl = text_el("headline", lx, 0, {"size": P_["hs"], "align": "left"}, None, nlines=P_.get("hlines", 2))
    cta = text_el("cta", lx, 0, {"size": P_["cs"], "align": "left"}, P_.get("cmax"), nlines=P_.get("clines"))
    ca = cta["_m"]["w"] * cta["_m"]["h"]
    # logo com área ~ CTA (relação de tamanho da peça-mestra), limitado pelo espaço ao lado da headline
    lw_ideal = (ca * LOGO_AR) ** 0.5 * P_.get("logo_k", 1.0)
    avail = rx - (lx + hl["_m"]["w"]) - P_["gap_logo"]
    lw = max(F["logo_min_width"]["otium"] + 2, min(lw_ideal, avail))
    lh = lw / LOGO_AR
    gap = P_["gap"]
    blk_h = hl["_m"]["h"] + gap + cta["_m"]["h"]
    # posição vertical: bloco de texto termina em bottom_y (topo de glifo -> base de glifo)
    glyph_top = P_["bottom_y"] - blk_h
    hl_y = glyph_top - hl["_m"]["y"]  # _m.y relativo a y=0
    hl["geometry"]["y"] = round(hl_y, 2)
    hl["_m"]["y"] = glyph_top
    cta_gtop = glyph_top + hl["_m"]["h"] + gap
    cta["geometry"]["y"] = round(cta_gtop - cta["_m"]["y"], 2)
    cta["_m"]["y"] = cta_gtop
    # logo: centro vertical no centro do bloco da headline
    hc = glyph_top + hl["_m"]["h"] / 2 + P_.get("logo_dy", 0)
    logo = logo_el(rx - lw, hc - lh / 2, lw)
    faixa_y = glyph_top - P_["pad_top"]
    hero_h = min(H, faixa_y + P_["overlap"])
    hero = el("hero")
    hero["geometry"].update({"x": 0, "y": 0, "width": W, "height": round(hero_h, 2)})
    hero["crop"] = cover("otium_spa", W, hero_h, P_.get("fx", 0.55))
    faixa = el("faixa")
    faixa["geometry"].update({"x": 0, "y": round(faixa_y, 2), "width": W, "height": round(H - faixa_y, 2)})
    return [hero, faixa, logo, hl, cta]


def banner(fk, P_):
    F = FORMATS[fk]
    W, H = F["width"], F["height"]
    hw = P_["hero_w"]
    hero = el("hero")
    hero["geometry"].update({"x": 0, "y": 0, "width": hw, "height": H})
    hero["crop"] = cover("otium_spa", hw, H, 0.5)
    faixa = el("faixa")
    faixa["geometry"].update({"x": hw, "y": 0, "width": W - hw, "height": H})
    lx = hw + P_["pad"]
    hl = text_el("headline", lx, 0, {"size": P_["hs"], "align": "left"}, None, nlines=1)
    cta = text_el("cta", lx, 0, {"size": P_["cs"], "align": "left"}, None, nlines=1)
    gap = P_["gap"]
    blk_h = hl["_m"]["h"] + gap + cta["_m"]["h"]
    gt = (H - blk_h) / 2 + P_.get("dy", 0)
    hl["geometry"]["y"] = round(gt - hl["_m"]["y"], 2); hl["_m"]["y"] = gt
    ct = gt + hl["_m"]["h"] + gap
    cta["geometry"]["y"] = round(ct - cta["_m"]["y"], 2); cta["_m"]["y"] = ct
    ca = cta["_m"]["w"] * cta["_m"]["h"]
    lw = max(F["logo_min_width"]["otium"] + 2, (ca * LOGO_AR) ** 0.5)
    lh = lw / LOGO_AR
    logo = logo_el(W - P_["right"] - lw, H / 2 - lh / 2, lw)
    return [hero, faixa, logo, hl, cta]


PLANS = {
    "post_1080x1350": (vertical, {"left": 84, "hs": 84, "cs": 30, "gap": 50, "gap_logo": 60, "bottom_y": 1350 - 150,
                                   "pad_top": 80, "overlap": 0, "fx": 0.53}),
    "card_1080x1080": (vertical, {"left": 80, "hs": 74, "cs": 28, "gap": 44, "gap_logo": 60, "bottom_y": 1080 - 110,
                                   "pad_top": 70, "overlap": 0, "fx": 0.5}),
    "stories_1080x1920": (vertical, {"left": 88, "hs": 84, "cs": 34, "gap": 54, "gap_logo": 50, "bottom_y": 1516 - 24,
                                      "pad_top": 90, "overlap": 0}),
    "email_600x1200": (vertical, {"left": 36, "hs": 50, "cs": 20, "gap": 30, "gap_logo": 26, "bottom_y": 1200 - 120,
                                   "pad_top": 64, "overlap": 0}),
    "banner_970x250": (banner, {"hero_w": 380, "pad": 30, "right": 24, "hs": 28, "cs": 15, "gap": 14}),
}


def lint(fk, els):
    """checagens locais (espelham as regras do brief)."""
    F = FORMATS[fk]
    W, H = F["width"], F["height"]
    m = F["margin"]
    sx, sy = m + F["safe"][3], m + F["safe"][0]
    sX, sY = W - m - F["safe"][1], H - m - F["safe"][2]
    probs = []
    by = {e["id"]: e for e in els}
    def bx(e):
        g = e["geometry"]; return (g["x"], g["y"], g["x"] + g["width"], g["y"] + g["height"])
    def ext(e):
        if "_m" in e:
            q = e["_m"]; return (q["x"], q["y"], q["x"] + q["w"], q["y"] + q["h"])
        return bx(e)
    def ov(a, b):
        return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    for e in els:
        x0, y0, x1, y1 = bx(e)
        if x0 < -0.5 or y0 < -0.5 or x1 > W + 0.5 or y1 > H + 0.5: probs.append(("canvas", e["id"]))
        if e["type"] == "TEXT":
            a = ext(e)
            if a[0] < sx or a[1] < sy or a[2] > sX or a[3] > sY: probs.append(("safe", e["id"], a))
            if a[3] > y1 + 1: probs.append(("overflow", e["id"]))
            if e["style"]["size"] < F["min_font"][next(s for s in SRC["elements"] if s["id"] == e["id"])["role"]]:
                probs.append(("minfont", e["id"]))
        if e["type"] == "IMAGE":
            a = ASSETS[e["asset"]]; c = e["crop"]
            arw = c[2] * a["width"] / (c[3] * a["height"]); arb = (x1 - x0) / (y1 - y0)
            if abs(arw / arb - 1) > 0.01: probs.append(("aspect", e["id"], arw, arb))
    lg = by["logo"]
    if lg["geometry"]["width"] < F["logo_min_width"]["otium"]: probs.append(("logo_min",))
    L = bx(lg)
    if L[0] < sx or L[1] < sy or L[2] > sX or L[3] > sY: probs.append(("logo_safe", L))
    for t in ("headline", "cta"):
        if ov(ext(by[t]), L) > 4: probs.append(("text_logo", t))
    if ov(ext(by["headline"]), ext(by["cta"])) > 4: probs.append(("text_text",))
    # faixa cobre os textos
    fx = bx(by["faixa"])
    for t in ("headline", "cta"):
        a = ext(by[t]); ar = (a[2] - a[0]) * (a[3] - a[1])
        if ov(a, fx) < 0.95 * ar: probs.append(("no_scrim", t))
    # relação de área logo x CTA
    ca = (ext(by["cta"])[2] - ext(by["cta"])[0]) * (ext(by["cta"])[3] - ext(by["cta"])[1])
    la = lg["geometry"]["width"] * lg["geometry"]["height"]
    ha = (ext(by["headline"])[2] - ext(by["headline"])[0]) * (ext(by["headline"])[3] - ext(by["headline"])[1])
    edges = [(lambda a: (a[0], (a[0] + a[2]) / 2, a[2]))(ext(by[i])) for i in ("headline", "cta", "logo")]
    for i in range(3):
        for j in range(i + 1, 3):
            for k in range(3):
                d = abs(edges[i][k] - edges[j][k])
                if 2 < d < 0.02 * W: probs.append(("quase_alinhado", i, j, k, round(d, 1)))
    info = {"cta/logo": round(ca / la, 2), "head/logo": round(ha / la, 2), "head/cta": round(ha / ca, 2),
            "hero_crop": by["hero"]["crop"], "lines": {t: by[t]["_m"]["lines"] for t in ("headline", "cta")}}
    return probs, info


def preview(fk, cand):
    """render aproximado em PIL só para olhar antes de gastar verificação."""
    W, H = cand["canvas"]["width"], cand["canvas"]["height"]
    img = Image.new("RGBA", (W, H), cand["canvas"]["background"])
    for e in sorted(cand["elements"], key=lambda e: e["geometry"]["z"]):
        g = e["geometry"]
        x, y, w, h = int(round(g["x"])), int(round(g["y"])), int(round(g["width"])), int(round(g["height"]))
        if e["type"] == "IMAGE":
            a = ASSETS[e["asset"]]; im = Image.open(P("assets", a["file"])).convert("RGBA"); c = e["crop"]
            box = (c[0] * im.width, c[1] * im.height, (c[0] + c[2]) * im.width, (c[1] + c[3]) * im.height)
            im = im.resize((w, h), Image.LANCZOS, box=box)
            img.alpha_composite(im, (x, y))
        elif e["type"] == "SHAPE":
            col = e["style"]["color"].lstrip("#"); rgb = tuple(int(col[i:i + 2], 16) for i in (0, 2, 4))
            ov = Image.new("RGBA", (w, h), rgb + (int(255 * e["style"].get("opacity", 1)),))
            img.alpha_composite(ov, (x, y))
        else:
            st = e["style"]; f = font(st["font"], st["weight"], int(round(st["size"])))
            d = ImageDraw.Draw(img); m = e["_m"]; a, _ = em_metrics(st)
            for i, ln in enumerate(m["lines"]):
                base = g["y"] + (m["L"] - m["ch"]) / 2 + i * m["L"] + a * st["size"]
                d.text((g["x"], base), ln, font=f, fill=st["color"], anchor="ls")
    os.makedirs(PREV, exist_ok=True)
    img.convert("RGB").save(os.path.join(PREV, f"{fk}.png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    for fk, (fn, params) in PLANS.items():
        if only and fk not in only:
            continue
        els = fn(fk, params)
        probs, info = lint(fk, els)
        F = FORMATS[fk]
        cand = {"schema_version": "bancada-0.1", "layout_id": SRC["layout_id"], "brand": SRC["brand"], "_format": fk,
                "canvas": {"width": F["width"], "height": F["height"], "background": SRC["canvas"]["background"]},
                "elements": els}
        if "--preview" in sys.argv:
            preview(fk, cand)
        clean = copy.deepcopy(cand)
        for e in clean["elements"]:
            e.pop("_m", None)
        json.dump(clean, open(os.path.join(OUT, f"otium_spa__{fk}.json"), "w"), ensure_ascii=False, indent=1)
        print(fk, "OK" if not probs else probs, json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
