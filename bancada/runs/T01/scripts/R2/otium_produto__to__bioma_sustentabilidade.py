#!/usr/bin/env python3
"""R2 — script de desdobramento escrito para a peça otium_produto.

Lê a peça-mestra, os formatos e os ativos; grava 5 candidatos em runs/T01/candidates/R2/.
Medição de texto com PIL (raqm) nas mesmas fontes do render; replica o modelo de linha do
Chromium (caixa de conteúdo = ascent+descent centrada na linha de line_height).
Uso: python3 runs/T01/scripts/R2/otium_produto.py [formato ...]
"""
import json, math, os, sys
from PIL import ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
P = lambda *a: os.path.join(ROOT, *a)
SRC = json.load(open(P("fixtures", "bioma_sustentabilidade.json")))
FMTS = json.load(open(P("fixtures", "formats.json")))
ASSETS = json.load(open(P("assets", "assets.json")))
OUT = P("runs", "T01", "candidates", "R2")

FONT_FILES = {("Archivo", 700): "Archivo-700.ttf", ("Host Grotesk", 600): "HostGrotesk-600.ttf",
              ("Poppins", 400): "Poppins-400.ttf"}
_fc = {}


def font(fam, w, size):
    k = (fam, w, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(P("fonts", FONT_FILES[(fam, w)]), size)
    return _fc[k]


def src_el(i):
    return next(e for e in SRC["elements"] if e["id"] == i)


def wrap(text, f, width):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w) if cur else w
        if f.getlength(t) <= width or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines


def balanced_width(eid, size, first_line):
    """Largura de caixa que quebra o texto logo depois de `first_line` (evita viúva/órfã)."""
    st = src_el(eid)["style"]; f = font(st["font"], st["weight"], size)
    txt = src_el(eid)["text"]; assert txt.startswith(first_line)
    nxt = txt[len(first_line):].strip().split(" ")[0]
    w1, w2 = f.getlength(first_line), f.getlength(first_line + " " + nxt)
    return math.ceil(w1 + (w2 - w1) * 0.5)


def text_block(eid, x, y, width, size, lh=None, align="left", force_lines=None):
    """Monta um TEXT e devolve (elemento, extensão medida estimada)."""
    s = dict(src_el(eid)["style"]); s["size"] = size; s["align"] = align
    if lh is not None: s["line_height"] = lh
    lh = s["line_height"]
    f = font(s["font"], s["weight"], 100)
    asc, desc = f.getmetrics()
    content = (asc + desc) / 100.0 * size
    fs = font(s["font"], s["weight"], size)
    lines = wrap(src_el(eid)["text"], fs, width * 0.985)  # folga p/ diferenças de shaping
    if force_lines: assert len(lines) == force_lines, (eid, lines)
    n = len(lines)
    lwid = [fs.getlength(l) for l in lines]
    mw = max(lwid)
    top = y + (lh * size - content) / 2
    bottom = y + (n - 1) * lh * size + (lh * size + content) / 2
    h = math.ceil(max(bottom - y, n * lh * size) + 4)
    if align == "left": mx = x
    elif align == "center": mx = x + (width - mw) / 2
    else: mx = x + width - mw
    el = {"id": eid, "type": "TEXT", "role": src_el(eid)["role"], "priority": src_el(eid)["priority"],
          "text": src_el(eid)["text"], "geometry": {"x": round(x), "y": round(y), "width": round(width), "height": h, "z": 5},
          "style": s}
    meas = {"x": mx, "y": top, "w": mw, "h": bottom - top, "lines": n, "bottom": bottom, "text_lines": lines}
    return el, meas


def cover_crop(asset, bw, bh, cx=None, cy=None):
    """Janela 'cover' sem distorção centrada no centro da área protegida (ou cx,cy normalizados)."""
    a = ASSETS[asset]; p = a["protected"]
    cx = p[0] + p[2] / 2 if cx is None else cx
    cy = p[1] + p[3] / 2 if cy is None else cy
    arB, arI = bw / bh, a["width"] / a["height"]
    if arI > arB: ch, cw = 1.0, arB / arI
    else: cw, ch = 1.0, arI / arB
    x = min(max(cx - cw / 2, 0), 1 - cw); y = min(max(cy - ch / 2, 0), 1 - ch)
    return [round(x, 5), round(y, 5), round(cw, 6), round(ch, 6)]


def hero(x, y, w, h, cx=None, cy=None):
    e = src_el("hero")
    cr = cover_crop(e["asset"], w, h, cx, cy)
    p = ASSETS[e["asset"]]["protected"]
    vis_x = min(p[0] + p[2], cr[0] + cr[2]) - max(p[0], cr[0])
    vis_y = min(p[1] + p[3], cr[1] + cr[3]) - max(p[1], cr[1])
    vis = max(0, vis_x) * max(0, vis_y) / (p[2] * p[3])
    return {"id": "hero", "type": "IMAGE", "role": "HERO", "priority": e["priority"], "asset": e["asset"],
            "geometry": {"x": x, "y": y, "width": w, "height": h, "z": 1}, "crop": cr}, vis


def logo(x, y, w):
    e = src_el("logo"); a = ASSETS[e["asset"]]
    h = round(w * a["height"] / a["width"], 2)
    return {"id": "logo", "type": "IMAGE", "role": "LOGO", "priority": e["priority"], "asset": e["asset"],
            "geometry": {"x": x, "y": y, "width": w, "height": h, "z": 6}, "crop": [0, 0, 1, 1]}


# ------------------------------------------------------------------ layouts por formato
# Regra geral: foto e texto nunca se tocam (o KV não usa texto sobre foto); texto sempre no
# fundo escuro da marca; ordem logo → título → selo → CTA; selo+CTA juntos (grupo ADJACENT);
# hierarquia 72>34>26 preservada em escala; logo sempre acima do mínimo e alinhado à coluna.

def L_email(F, extra=0):
    W, H, m = F["width"], F["height"], F["margin"]
    col = W - 2 * m
    els, ms = [], {}
    lg = logo(m, 44, 150); els.append(lg)
    hy = 44 + lg["geometry"]["height"] + 40
    hh = 600 + extra
    h, vis = hero(0, round(hy), W, hh); els.append(h)
    y = hy + hh + 52
    t, mm = text_block("headline", m, y, min(col, balanced_width("headline", 44, "Jardim das Perdizes,")), 44, force_lines=2); els.append(t); ms["headline"] = mm
    y = mm["bottom"] + 30
    t, mm = text_block("selo", m, y, col, 22); els.append(t); ms["selo"] = mm
    y = mm["bottom"] + 16
    t, mm = text_block("cta", m, y, col, 17); els.append(t); ms["cta"] = mm
    return els, ms, vis


def L_post(F, extra=0):
    W, H, m = F["width"], F["height"], F["margin"]
    col = W - 2 * m
    els, ms = [], {}
    hh = 740 + extra
    h, vis = hero(0, 0, W, hh); els.append(h)
    lg = logo(m, hh + 52, 260); els.append(lg)
    y = hh + 56 + lg["geometry"]["height"] + 44
    t, mm = text_block("headline", m, y, min(col, balanced_width("headline", 62, "Jardim das Perdizes,")), 62, force_lines=2); els.append(t); ms["headline"] = mm
    y = mm["bottom"] + 34
    t, mm = text_block("selo", m, y, col, 32); els.append(t); ms["selo"] = mm
    y = mm["bottom"] + 18
    t, mm = text_block("cta", m, y, col, 26); els.append(t); ms["cta"] = mm
    return els, ms, vis


def L_card(F, extra=0):
    W, H, m = F["width"], F["height"], F["margin"]
    col = W - 2 * m
    els, ms = [], {}
    hh = 560 + extra
    h, vis = hero(0, 0, W, hh); els.append(h)
    lg = logo(m, hh + 40, 230); els.append(lg)
    y = hh + 44 + lg["geometry"]["height"] + 34
    t, mm = text_block("headline", m, y, col, 54, force_lines=1); els.append(t); ms["headline"] = mm
    y = mm["bottom"] + 28
    t, mm = text_block("selo", m, y, col, 31); els.append(t); ms["selo"] = mm
    y = mm["bottom"] + 14
    t, mm = text_block("cta", m, y, col, 26); els.append(t); ms["cta"] = mm
    return els, ms, vis


def L_stories(F, extra=0):
    W, H, m = F["width"], F["height"], F["margin"]
    top = m + F["safe"][0]
    col = W - 2 * m
    els, ms = [], {}
    lg = logo(m, top, 290); els.append(lg)
    y = top + lg["geometry"]["height"] + 64
    t, mm = text_block("headline", m, y, min(col, balanced_width("headline", 76, "Jardim das Perdizes,")), 76, force_lines=2); els.append(t); ms["headline"] = mm
    y = mm["bottom"] + 40
    t, mm = text_block("selo", m, y, col, 38); els.append(t); ms["selo"] = mm
    y = mm["bottom"] + 22
    t, mm = text_block("cta", m, y, col, 31); els.append(t); ms["cta"] = mm
    hy = round(mm["bottom"] + 70)
    h, vis = hero(0, hy, W, H - hy); els.append(h)
    return els, ms, vis


def L_banner(F, extra=0):
    W, H, m = F["width"], F["height"], F["margin"]
    els, ms = [], {}
    hw = 340
    h, vis = hero(0, 0, hw, H); els.append(h)
    x = hw + 30
    col = W - m - x
    lg = logo(x, 18 + extra // 2, 140); els.append(lg)
    y = 18 + extra // 2 + lg["geometry"]["height"] + 14
    t, mm = text_block("headline", x, y, col, 35, force_lines=1); els.append(t); ms["headline"] = mm
    y = mm["bottom"] + 16
    t, mm = text_block("selo", x, y, col, 19); els.append(t); ms["selo"] = mm
    y = mm["bottom"] + 9
    t, mm = text_block("cta", x, y, col, 16); els.append(t); ms["cta"] = mm
    return els, ms, vis


LAYOUTS = {"email_600x1200": L_email, "post_1080x1350": L_post, "card_1080x1080": L_card,
           "stories_1080x1920": L_stories, "banner_970x250": L_banner}


# ------------------------------------------------------------------ autoverificação (estimada)
def selfcheck(fk, F, els, ms, vis):
    W, H, m = F["width"], F["height"], F["margin"]
    sf = F["safe"]
    safe = (m + sf[3], m + sf[0], W - m - sf[1], H - m - sf[2])
    probs = []
    by = {e["id"]: e for e in els}
    for e in els:
        g = e["geometry"]
        if g["x"] < -0.5 or g["y"] < -0.5 or g["x"] + g["width"] > W + 0.5 or g["y"] + g["height"] > H + 0.5:
            probs.append(f"{e['id']} fora do canvas")
        if e["type"] == "TEXT":
            mm = ms[e["id"]]
            if mm["y"] + mm["h"] > g["y"] + g["height"] + 1.5: probs.append(f"{e['id']} estouro vertical")
            if mm["x"] + mm["w"] > g["x"] + g["width"] + 1.5: probs.append(f"{e['id']} estouro horizontal")
            if not (mm["x"] >= safe[0] - 1 and mm["y"] >= safe[1] - 1 and mm["x"] + mm["w"] <= safe[2] + 1 and mm["y"] + mm["h"] <= safe[3] + 1):
                probs.append(f"{e['id']} fora da área segura")
            if e["style"]["size"] < F["min_font"][e["role"]]: probs.append(f"{e['id']} corpo < mínimo")
            hb = by["hero"]["geometry"]
            if mm["x"] < hb["x"] + hb["width"] and mm["x"] + mm["w"] > hb["x"] and mm["y"] < hb["y"] + hb["height"] and mm["y"] + mm["h"] > hb["y"]:
                probs.append(f"{e['id']} sobre a foto")
    lg = by["logo"]["geometry"]
    if lg["width"] < F["logo_min_width"]["otium"]: probs.append("logo pequeno")
    if not (lg["x"] >= safe[0] - 1 and lg["y"] >= safe[1] - 1 and lg["x"] + lg["width"] <= safe[2] + 1 and lg["y"] + lg["height"] <= safe[3] + 1):
        probs.append("logo fora da área segura")
    for e in els:
        if e["type"] == "TEXT":
            mm = ms[e["id"]]
            if mm["x"] < lg["x"] + lg["width"] and mm["x"] + mm["w"] > lg["x"] and mm["y"] < lg["y"] + lg["height"] and mm["y"] + mm["h"] > lg["y"]:
                probs.append(f"{e['id']} encosta no logo")
    tids = ["headline", "selo", "cta"]
    for i in range(3):
        for j in range(i + 1, 3):
            a, b = ms[tids[i]], ms[tids[j]]
            if a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"] and a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]:
                probs.append(f"{tids[i]}/{tids[j]} sobrepostos")
    if vis < 0.8: probs.append(f"área protegida só {vis:.2f}")
    # suaves estimadas
    edges = [[ms[t]["x"], ms[t]["x"] + ms[t]["w"] / 2, ms[t]["x"] + ms[t]["w"]] for t in tids]
    edges.append([lg["x"], lg["x"] + lg["width"] / 2, lg["x"] + lg["width"]])
    near = sum(1 for i in range(4) for j in range(i + 1, 4) for k in range(3) if 2 < abs(edges[i][k] - edges[j][k]) < 0.02 * W)
    ar = {t: ms[t]["w"] * ms[t]["h"] for t in tids}
    ar["logo"] = lg["width"] * lg["height"]; hb = by["hero"]["geometry"]; ar["hero"] = hb["width"] * hb["height"]
    rel = lambda a, b: 1 if a > b * 1.2 else (-1 if a < b / 1.2 else 0)
    want = {("hero", "logo"): 1, ("hero", "headline"): 1, ("hero", "selo"): 1, ("hero", "cta"): 1,
            ("logo", "headline"): -1, ("logo", "selo"): 1, ("logo", "cta"): 1,
            ("headline", "selo"): 1, ("headline", "cta"): 1, ("selo", "cta"): 0}
    bad = [f"{a}/{b}:{ar[a]/ar[b]:.2f}" for (a, b), v in want.items() if rel(ar[a], ar[b]) != v]
    sr = 1 - len(bad) / len(want)
    k = math.sqrt(W * H / (1920 * 1080))
    esc = sum(min(1, by[t]["style"]["size"] / max(F["min_font"][by[t]["role"]], src_el(t)["style"]["size"] * k)) for t in tids) / 3
    # preenchimento
    N, cov = 40, 0
    boxes = [(e["geometry"]["x"], e["geometry"]["y"], e["geometry"]["width"], e["geometry"]["height"]) if e["type"] != "TEXT"
             else (ms[e["id"]]["x"], ms[e["id"]]["y"], ms[e["id"]]["w"], ms[e["id"]]["h"]) for e in els]
    for i in range(N):
        for j in range(N):
            x, y = (i + .5) / N * W, (j + .5) / N * H
            if any(bx <= x <= bx + bw and by_ <= y <= by_ + bh for bx, by_, bw, bh in boxes): cov += 1
    fill = min(1, cov / N / N / 0.8)
    gap = max(0, ms["cta"]["y"] - (ms["selo"]["y"] + ms["selo"]["h"]))
    info = {"near_align": near, "size_rel": round(sr, 2), "sr_bad": bad, "escala": round(esc, 3), "fill": round(fill, 3),
            "grupo_ok": gap <= 0.12 * min(W, H), "vis": round(vis, 3),
            "lines": {t: ms[t]["text_lines"] for t in tids}}
    return probs, info


def build(fk):
    F = FMTS[fk]
    els, ms, vis = LAYOUTS[fk](F)
    # sobra vertical: a foto (ou o bloco, no banner) absorve o que faltar até a margem inferior
    if fk != "stories_1080x1920":
        slack = int(F["height"] - F["margin"] - F["safe"][2] - ms["cta"]["bottom"]) - 6
        if slack > 0:
            els, ms, vis = LAYOUTS[fk](F, slack)
    order = {"hero": 0, "logo": 1, "headline": 2, "selo": 3, "cta": 4}
    els.sort(key=lambda e: order[e["id"]])
    cand = {"schema_version": "bancada-0.1", "layout_id": SRC["layout_id"], "brand": SRC["brand"], "_format": fk,
            "canvas": {"width": F["width"], "height": F["height"], "background": SRC["canvas"]["background"]},
            "elements": els, "relations": SRC["relations"], "groups": SRC["groups"], "text_over_image": [],
            "_arm": "R2"}
    probs, info = selfcheck(fk, F, els, ms, vis)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"bioma_sustentabilidade__{fk}.json"), "w") as fh:
        json.dump(cand, fh, indent=1, ensure_ascii=False)
    print(fk, "PROBLEMAS:" if probs else "ok", probs, json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    for fk in (sys.argv[1:] or list(LAYOUTS)):
        build(fk)
