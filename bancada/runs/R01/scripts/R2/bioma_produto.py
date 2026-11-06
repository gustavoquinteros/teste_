#!/usr/bin/env python3
"""R2 — script de desdobramento escrito pela IA para a peca bioma_produto.

Le fixtures/bioma_produto.json, fixtures/formats.json, assets/assets.json e grava
runs/R01/candidates/R2/bioma_produto__<formato>.json para os 5 formatos.

Ideia de layout (peca-mestra = painel verde com texto a esquerda + foto da fachada a direita):
  - post / email : pilha vertical  logo+headline | foto sangrada | selo+cta+legal
  - card         : split como a mestra (texto a esquerda, foto sangrada a direita)
  - stories      : foto sangrada no topo (a faixa de UI do topo fica sobre a foto),
                   bloco de texto dentro da area segura, rodape livre
  - banner       : logo | headline+selo+cta+legal | foto sangrada a direita
Texto medido com PIL nas mesmas fontes (fonts/*.ttf, Inter do sistema), com quebra gulosa
por espacos e folga, e caixa calculada pela extensao real dos glifos (ascent+descent).
"""
import json, math, os, sys
from PIL import ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
LAYOUT = "bioma_produto"
OUT = os.path.join(ROOT, "runs", "R01", "candidates", "R2")

SRC = json.load(open(os.path.join(ROOT, "fixtures", LAYOUT + ".json")))
FMTS = json.load(open(os.path.join(ROOT, "fixtures", "formats.json")))
ASSETS = json.load(open(os.path.join(ROOT, "assets", "assets.json")))
BY = {e["id"]: e for e in SRC["elements"]}

FONT_FILES = {
    ("Cormorant Garamond", 600): "fonts/CormorantGaramond-600.ttf",
    ("Cormorant Garamond", 500): "fonts/CormorantGaramond-500.ttf",
    ("Barlow", 600): "fonts/Barlow-600.ttf",
    ("Barlow", 400): "fonts/Barlow-400.ttf",
}
INTER = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"
_fc = {}


def font(name, weight, size):
    k = (name, weight, size)
    if k not in _fc:
        p = FONT_FILES.get((name, weight))
        p = os.path.join(ROOT, p) if p else INTER
        _fc[k] = ImageFont.truetype(p, 1000)  # mede em 1000 e escala (subpixel estavel)
    return _fc[k]


# ------------------------------------------------------------------ medicao de texto
SLACK_W = 1.012  # folga de largura (diferencas de shaping PIL x Chromium)


def wrap(text, st, width):
    f = font(st["font"], st["weight"], 1000)
    s = st["size"] / 1000.0
    L = lambda t: f.getlength(t) * s * SLACK_W
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        t = w if not cur else cur + " " + w
        if L(t) <= width or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines, max(L(l) for l in lines)


def metrics(st):
    f = font(st["font"], st["weight"], 1000)
    a, d = f.getmetrics()
    return a / 1000.0, d / 1000.0


def measure(text, st, width):
    """-> dict(lines, w, top, h, box_h): top/h = extensao real relativa ao topo da caixa."""
    lines, w = wrap(text, st, width)
    a, d = metrics(st)
    size, lh = st["size"], st["line_height"] * st["size"]
    ch = (a + d) * size
    top = (lh - ch) / 2.0
    n = len(lines)
    bottom = (n - 1) * lh + top + ch
    box_h = math.ceil(max(n * lh, bottom) + 3)
    return {"lines": lines, "n": n, "w": w, "top": top, "h": bottom - top, "box_h": box_h}


def text_el(eid, x, y, width, size, align="left", lh=None):
    s = BY[eid]
    st = dict(s["style"]); st["size"] = size; st["align"] = align
    if lh:
        st["line_height"] = lh
    m = measure(s["text"], st, width)
    el = {"id": eid, "type": "TEXT", "role": s["role"], "priority": s["priority"], "text": s["text"],
          "geometry": {"x": round(x, 2), "y": round(y, 2), "width": round(width, 2), "height": m["box_h"], "z": 5},
          "style": st}
    el["_m"] = m
    return el


def ext(el):
    """extensao estimada do texto (como o verificador mede)."""
    g, m = el["geometry"], el["_m"]
    w = m["w"]
    x = g["x"] if el["style"]["align"] == "left" else g["x"] + (g["width"] - w) / 2
    return {"x": x, "y": g["y"] + m["top"], "w": w, "h": m["h"]}


# ------------------------------------------------------------------ imagens
def cover_crop(asset, bw, bh, focus=None):
    a = ASSETS[asset]
    arA, arB = a["width"] / a["height"], bw / bh
    if arB >= arA:
        cw, ch = 1.0, arA / arB
    else:
        cw, ch = arB / arA, 1.0
    p = a["protected"]
    fx, fy = focus or (p[0] + p[2] / 2, p[1] + p[3] / 2)
    cx = min(max(fx - cw / 2, 0), 1 - cw)
    cy = min(max(fy - ch / 2, 0), 1 - ch)
    return [round(cx, 5), round(cy, 5), round(cw, 5), round(ch, 5)]


def protected_vis(asset, crop):
    p = ASSETS[asset]["protected"]
    ix = max(0, min(p[0] + p[2], crop[0] + crop[2]) - max(p[0], crop[0]))
    iy = max(0, min(p[1] + p[3], crop[1] + crop[3]) - max(p[1], crop[1]))
    return ix * iy / (p[2] * p[3])


def hero_el(x, y, w, h, focus=None):
    s = BY["hero"]
    crop = cover_crop(s["asset"], w, h, focus)
    return {"id": "hero", "type": "IMAGE", "role": "HERO", "priority": s["priority"], "asset": s["asset"],
            "geometry": {"x": round(x, 2), "y": round(y, 2), "width": round(w, 2), "height": round(h, 2), "z": 1},
            "crop": crop}


def logo_el(x, y, w):
    s = BY["logo"]
    a = ASSETS[s["asset"]]
    h = w * a["height"] / a["width"]
    return {"id": "logo", "type": "IMAGE", "role": "LOGO", "priority": s["priority"], "asset": s["asset"],
            "geometry": {"x": round(x, 2), "y": round(y, 2), "width": round(w, 2), "height": round(h, 2), "z": 6},
            "crop": [0, 0, 1, 1]}


# ------------------------------------------------------------------ layouts por formato
def lay_post(F):
    W, H, M = F["width"], F["height"], F["margin"]
    tw = W - 2 * M
    logo = logo_el(M, M, 210)
    lg = logo["geometry"]
    hl = text_el("headline", M, lg["y"] + lg["height"] + 46, tw, 60)
    # bloco inferior ancorado na margem de baixo
    legal = text_el("legal", M, 0, tw, 14)
    selo = text_el("selo", M, 0, tw, 32)
    cta = text_el("cta", M, 0, tw, 28)
    yb = H - M - legal["_m"]["box_h"]
    legal["geometry"]["y"] = yb
    cta["geometry"]["y"] = yb - 40 - cta["_m"]["box_h"]
    selo["geometry"]["y"] = cta["geometry"]["y"] - 10 - selo["_m"]["box_h"]
    y0 = hl["geometry"]["y"] + hl["geometry"]["height"] + 40
    y1 = selo["geometry"]["y"] - 44
    hero = hero_el(0, y0, W, y1 - y0)
    return [hero, logo, hl, selo, cta, legal]


def lay_email(F):
    W, H, M = F["width"], F["height"], F["margin"]
    tw = W - 2 * M
    logo = logo_el(M, M + 8, 160)
    lg = logo["geometry"]
    hl = text_el("headline", M, lg["y"] + lg["height"] + 30, tw, 42)
    legal = text_el("legal", M, 0, tw, 9.5)
    selo = text_el("selo", M, 0, tw, 22)
    cta = text_el("cta", M, 0, tw, 18)
    yb = H - M - legal["_m"]["box_h"]
    legal["geometry"]["y"] = yb
    cta["geometry"]["y"] = yb - 30 - cta["_m"]["box_h"]
    selo["geometry"]["y"] = cta["geometry"]["y"] - 6 - selo["_m"]["box_h"]
    y0 = hl["geometry"]["y"] + hl["geometry"]["height"] + 28
    y1 = selo["geometry"]["y"] - 30
    hero = hero_el(0, y0, W, y1 - y0)
    return [hero, logo, hl, selo, cta, legal]


def lay_card(F, shrink=0, hw=0, cs=26, ss=29, hs=52):
    W, H, M = F["width"], F["height"], F["margin"]
    xp = 560  # foto ocupa a metade direita, sangrada (520px: ~88% do predio visivel)
    tw = xp - 2 * M + 10
    logo = logo_el(M, M, 190)
    lg = logo["geometry"]
    hl = text_el("headline", M, lg["y"] + lg["height"] + 50, tw - hw, hs)
    legal = text_el("legal", M, 0, tw - shrink, 14)
    legal["geometry"]["y"] = H - M - legal["_m"]["box_h"]
    selo = text_el("selo", M, hl["geometry"]["y"] + hl["geometry"]["height"] + 44, tw, ss)
    cta = text_el("cta", M, selo["geometry"]["y"] + selo["geometry"]["height"] + 12, tw, cs)
    hero = hero_el(xp, 0, W - xp, H)
    return [hero, logo, hl, selo, cta, legal]


def lay_stories(F, shrink=0, hw=0, cs=34, ss=40):
    W, H, M = F["width"], F["height"], F["margin"]
    sy = M + F["safe"][0]
    sb = H - M - F["safe"][2]
    tw = W - 2 * M
    logo = logo_el(M, sy, 250)
    hl = text_el("headline", M, 0, tw - hw, 76)
    selo = text_el("selo", M, 0, tw, ss)
    cta = text_el("cta", M, 0, tw, cs)
    legal = text_el("legal", M, 0, tw - shrink, 17)
    gaps = [40, 48, 14, 48]  # logo>hl, hl>selo, selo>cta, cta>legal
    stack = [logo, hl, selo, cta, legal]
    hs = [logo["geometry"]["height"]] + [e["_m"]["box_h"] for e in stack[1:]]
    y = sy
    for i, e in enumerate(stack):
        e["geometry"]["y"] = round(y, 2)
        y += hs[i] + (gaps[i] if i < len(gaps) else 0)
    assert y <= sb, "stack nao cabe na area segura"
    y0 = y + 56  # foto sangrada ate a borda de baixo (zona de UI sem texto)
    hero = hero_el(0, y0, W, H - y0)
    return [hero, logo, hl, selo, cta, legal]


def lay_banner(F, shrink=0, hw=0, cs=14.5, ss=17):
    W, H, M = F["width"], F["height"], F["margin"]
    xp = 700  # foto a direita sangrada
    logo = logo_el(M + 8, 0, 130)
    tx = logo["geometry"]["x"] + 130 + 26
    tw = xp - 24 - tx
    hl = text_el("headline", tx, 0, tw - hw, 30)
    selo = text_el("selo", tx, 0, tw, ss)
    cta = text_el("cta", tx, 0, tw, cs)
    legal = text_el("legal", tx, 0, tw - shrink, 8)
    stack = [hl, selo, cta, legal]
    gaps = [8, 3, 9]
    hs = [e["_m"]["box_h"] for e in stack]
    total = sum(hs) + sum(gaps)
    y = (H - total) / 2
    for i, e in enumerate(stack):
        e["geometry"]["y"] = round(y, 2)
        y += hs[i] + (gaps[i] if i < len(gaps) else 0)
    # logo alinhado ao topo da extensao do headline
    logo["geometry"]["y"] = round(hl["geometry"]["y"] + hl["_m"]["top"] + 2, 2)
    hero = hero_el(xp, 0, W - xp, H)
    return [hero, logo, hl, selo, cta, legal]


LAYOUTS = {"email_600x1200": lay_email, "post_1080x1350": lay_post, "card_1080x1080": lay_card,
           "stories_1080x1920": lay_stories, "banner_970x250": lay_banner}


# ------------------------------------------------------------------ auto-checagem local
def inter(a, b):
    x, y = max(a["x"], b["x"]), max(a["y"], b["y"])
    X, Y = min(a["x"] + a["w"], b["x"] + b["w"]), min(a["y"] + a["h"], b["y"] + b["h"])
    return (X - x) * (Y - y) if X > x and Y > y else 0


def bx(e):
    g = e["geometry"]; return {"x": g["x"], "y": g["y"], "w": g["width"], "h": g["height"]}


def report(fk, F, els):
    W, H, M = F["width"], F["height"], F["margin"]
    safe = {"x": M + F["safe"][3], "y": M + F["safe"][0], "w": W - 2 * M - F["safe"][1] - F["safe"][3],
            "h": H - 2 * M - F["safe"][0] - F["safe"][2]}
    probs = []
    E = {e["id"]: (ext(e) if e["type"] == "TEXT" else bx(e)) for e in els}
    for e in els:
        r = E[e["id"]]
        if e["type"] == "TEXT":
            mf = F["min_font"][e["role"]]
            if e["style"]["size"] < mf: probs.append(f"{e['id']} corpo<{mf}")
            if r["x"] < safe["x"] - 1 or r["y"] < safe["y"] - 1 or r["x"] + r["w"] > safe["x"] + safe["w"] + 1 or r["y"] + r["h"] > safe["y"] + safe["h"] + 1:
                probs.append(f"{e['id']} fora area segura {r}")
        b = bx(e)
        if b["x"] < -0.5 or b["y"] < -0.5 or b["x"] + b["w"] > W + .5 or b["y"] + b["h"] > H + .5:
            probs.append(f"{e['id']} fora do canvas")
    tx = [e for e in els if e["type"] == "TEXT"]
    for i in range(len(tx)):
        for j in range(i + 1, len(tx)):
            if inter(E[tx[i]["id"]], E[tx[j]["id"]]) > 4: probs.append(f"{tx[i]['id']}/{tx[j]['id']} sobrepostos")
    hb = bx(els[0])
    for t in tx + [els[1]]:
        if inter(E[t["id"]], hb) > 4: probs.append(f"{t['id']} sobre a foto")
    vis = protected_vis("bioma_fachada", els[0]["crop"])
    # alinhamento
    edges = [[E[i]["x"], E[i]["x"] + E[i]["w"] / 2, E[i]["x"] + E[i]["w"]] for i in ["logo", "headline", "selo", "cta", "legal"]]
    near = sum(1 for i in range(5) for j in range(i + 1, 5) for k in range(3) if 2 < abs(edges[i][k] - edges[j][k]) < 0.02 * W)
    # preenchimento
    N, cov = 40, 0
    for i in range(N):
        for j in range(N):
            x, y = (i + .5) / N * W, (j + .5) / N * H
            if any(r["x"] <= x <= r["x"] + r["w"] and r["y"] <= y <= r["y"] + r["h"] for r in E.values()): cov += 1
    fill = min(1, cov / N / N / 0.8)
    areas = {k: v["w"] * v["h"] for k, v in E.items()}
    print(f"{fk}: nearpad={near_pairs(F, els)} probs={probs} vis={vis:.2f} near={near} fill={fill:.2f} "
          f"sizes={[ (e['id'], e['style']['size'], e['_m']['n']) for e in tx]} "
          f"areas={ {k: int(v) for k, v in areas.items()} }")


def near_pairs(F, els, pad=6):
    W = F["width"]
    E = {e["id"]: (ext(e) if e["type"] == "TEXT" else bx(e)) for e in els}
    t = ["logo", "headline", "selo", "cta", "legal"]
    ed = {i: [E[i]["x"], E[i]["x"] + E[i]["w"] / 2, E[i]["x"] + E[i]["w"]] for i in t}
    return [(a, b, k) for x, a in enumerate(t) for b in t[x + 1:] for k in range(3)
            if 1.0 < abs(ed[a][k] - ed[b][k]) < 0.02 * W + pad]


GRID = {  # variacoes pequenas e legitimas (largura de coluna, corpo do selo/cta) para fugir de quase-alinhamentos
    "card_1080x1080": dict(cs=[26, 27], ss=[29, 30, 31], hw=[0, 20, 40], hs=[48, 50, 52, 54, 56]),
    "banner_970x250": dict(cs=[14, 14.5, 15], ss=[16, 17, 18], hw=[0, 20, 40, 60]),
    "stories_1080x1920": dict(cs=[34], ss=[40], hw=[0, 40, 80]),
}


def build(fk, F):
    fn = LAYOUTS[fk]
    if fk not in GRID:
        return fn(F)
    import itertools
    g = GRID[fk]
    best = None
    for cs, ss, hw, hs in itertools.product(g["cs"], g["ss"], g["hw"], g.get("hs", [None])):
        if ss <= cs:
            continue
        kw = {"hs": hs} if hs else {}
        for sh in range(0, 44, 4):  # coluna do legal encolhe no maximo 40px (legibilidade)
            els = fn(F, sh, hw, cs, ss, **kw)
            E = {e["id"]: (ext(e) if e["type"] == "TEXT" else bx(e)) for e in els}
            A = {k: v["w"] * v["h"] for k, v in E.items()}
            # preserva as relacoes de tamanho da mestra: headline >> legal, selo ~ cta
            viol = (A["headline"] < 1.25 * A["legal"]) + (max(A["selo"], A["cta"]) > 1.15 * min(A["selo"], A["cta"]))
            hlm = next(e for e in els if e["id"] == "headline")["_m"]
            widow = hlm["n"] > 1 and " " not in hlm["lines"][-1]  # palavra orfa na ultima linha do titulo
            n = len(near_pairs(F, els)) + 3 * viol + 5 * widow
            key = (n, hw + sh, -(hs or 0))
            if best is None or key < best[0]:
                best = (key, (sh, hw, cs, ss, kw))
    sh, hw, cs, ss, kw = best[1]
    print(f"  {fk}: grid best pen={best[0][0]} shrink={sh} hw={hw} cta={cs} selo={ss} {kw}")
    return fn(F, sh, hw, cs, ss, **kw)


def main():
    only = sys.argv[1:] or list(LAYOUTS)
    os.makedirs(OUT, exist_ok=True)
    for fk in only:
        F = FMTS[fk]
        els = build(fk, F)
        report(fk, F, els)
        clean = []
        for e in els:
            e = {k: v for k, v in e.items() if not k.startswith("_")}
            clean.append(e)
        cand = {"schema_version": "bancada-0.1", "layout_id": LAYOUT, "brand": SRC["brand"], "_format": fk,
                "canvas": {"width": F["width"], "height": F["height"], "background": SRC["canvas"]["background"]},
                "elements": clean, "relations": SRC.get("relations", []), "groups": SRC.get("groups", []),
                "text_over_image": []}
        json.dump(cand, open(os.path.join(OUT, f"{LAYOUT}__{fk}.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
