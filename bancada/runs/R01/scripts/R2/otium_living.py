#!/usr/bin/env python3
"""R2 — script de desdobramento proprio para a peca otium_living.

Le fixtures/otium_living.json, fixtures/formats.json, assets/assets.json e grava
runs/R01/candidates/R2/otium_living__<formato>.json para os 5 formatos.

Ideia de direcao de arte: a peca-mestra e "foto em cima + faixa escura embaixo com
logo + titulo + selo". Mantemos isso: foto sangrando no topo (ou a esquerda no banner),
recortada em volta do sofa (area protegida), e o bloco de marca/texto sempre sobre o
fundo escuro do canvas (nunca texto sobre foto -> contraste garantido, sem faixa).
Medicao de texto com PIL (raqm, mesmas TTFs que o Chromium carrega).
"""
import json, math, os, sys
from PIL import ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
L = "otium_living"
OUT = os.path.join(ROOT, "runs", "R01", "candidates", "R2")

src = json.load(open(os.path.join(ROOT, "fixtures", L + ".json")))
FMT = json.load(open(os.path.join(ROOT, "fixtures", "formats.json")))
AS = json.load(open(os.path.join(ROOT, "assets", "assets.json")))
S = {e["id"]: e for e in src["elements"]}

FONTFILES = {("Archivo", 700): "Archivo-700.ttf", ("Archivo", 400): "Archivo-400.ttf",
             ("Host Grotesk", 400): "HostGrotesk-400.ttf", ("Host Grotesk", 600): "HostGrotesk-600.ttf"}
_fc = {}


def font(style, size):
    k = (style["font"], int(style["weight"]), size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(os.path.join(ROOT, "fonts", FONTFILES[(k[0], k[1])]), size)
    return _fc[k]


def width(text, style, size):
    return font(style, size).getlength(text)


def wrap(text, style, size, maxw):
    """quebra gulosa igual ao navegador (white-space normal)."""
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w) if cur else w
        if not cur or width(t, style, size) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines


def wrap_margin(text, style, size, maxw):
    """folga minima (px) entre a quebra prevista e a decisao oposta — mede o risco de quebra diferente."""
    words, cur, m = text.split(" "), "", 1e9
    for w in words:
        t = (cur + " " + w) if cur else w
        if not cur:
            cur = t; continue
        tw = width(t, style, size)
        m = min(m, abs(tw - maxw))
        cur = t if tw <= maxw else w
    m = min(m, maxw - max(width(l, style, size) for l in wrap(text, style, size, maxw)))
    return m


def block(text, style, size, maxw):
    """linhas, largura real, altura que a caixa precisa e deslocamento do topo do 1o glifo."""
    lh = style["line_height"]
    lines = wrap(text, style, size, maxw)
    a, d = font(style, size).getmetrics()
    content = a + d
    Lh = size * lh
    top = (Lh - content) / 2               # topo do retangulo da 1a linha (pode ser negativo)
    bottom = (len(lines) - 1) * Lh + Lh / 2 + content / 2
    w = max(width(l, style, size) for l in lines)
    return {"lines": lines, "w": w, "h": math.ceil(max(len(lines) * Lh, bottom) + 4), "top": top,
            "ink_h": bottom - min(0, top), "margin": wrap_margin(text, style, size, maxw)}


def text_el(eid, x, y, w, size, align="left", h=None):
    s = S[eid]
    st = dict(s["style"]); st["size"] = size; st["align"] = align
    b = block(s["text"], st, size, w)
    pad_top = max(0, -b["top"]) + 1     # empurra a caixa para o glifo nao subir acima de y
    e = {"id": eid, "type": "TEXT", "role": s["role"], "priority": s["priority"], "text": s["text"],
         "geometry": {"x": round(x), "y": round(y + pad_top), "width": round(w), "height": h or b["h"], "z": s["geometry"]["z"]},
         "style": st}
    # extensao prevista (como o verificador mede)
    gx = e["geometry"]["x"]
    if align == "center":
        mx = gx + (w - b["w"]) / 2
    elif align == "right":
        mx = gx + w - b["w"]
    else:
        mx = gx
    e["_pred"] = {"x": mx, "y": e["geometry"]["y"] + min(0, b["top"]), "w": b["w"], "h": b["ink_h"], "lines": b["lines"], "margin": b["margin"]}
    return e


def logo_el(x, y, w):
    a = AS["otium_logo"]
    h = w * a["height"] / a["width"]
    s = S["logo"]
    return {"id": "logo", "type": "IMAGE", "role": "LOGO", "priority": s["priority"], "asset": "otium_logo",
            "geometry": {"x": round(x), "y": round(y), "width": round(w), "height": round(h), "z": s["geometry"]["z"]},
            "crop": [0, 0, 1, 1]}


def logo_h(w):
    a = AS["otium_logo"]; return round(w * a["height"] / a["width"])


def hero_el(x, y, w, h, cx=0.40, cy=0.69):
    """janela de recorte com o mesmo aspecto da caixa, centrada no sofa (area protegida)."""
    a = AS["otium_living"]
    ar_box = w / h
    ch = 1.0
    cw = ch * ar_box * a["height"] / a["width"]
    if cw > 1:
        cw = 1.0; ch = cw * a["width"] / a["height"] / ar_box
    p = a["protected"]
    x0 = min(max(cx - cw / 2, 0), 1 - cw)
    # garante a area protegida inteira dentro da janela, se couber
    if cw >= p[2]:
        x0 = min(max(x0, p[0] + p[2] - cw), p[0])
        x0 = min(max(x0, 0), 1 - cw)
    y0 = min(max(cy - ch / 2, 0), 1 - ch)
    s = S["hero"]
    return {"id": "hero", "type": "IMAGE", "role": "HERO", "priority": s["priority"], "asset": "otium_living",
            "geometry": {"x": x, "y": y, "width": w, "height": h, "z": s["geometry"]["z"]},
            "crop": [round(x0, 4), round(y0, 4), round(cw, 4), round(ch, 4)],
            "_upscale": (w / cw) / a["real_size"][0]}


# ------------------------------------------------------------------ formatos
def vstack(F, W, H, hero_h, logo_w, hl_size, selo_size, align, colx, colw, band_top, band_bot,
           gap_logo, gap_txt, hl_w=None):
    """coluna unica: logo, titulo, selo, centrada verticalmente na faixa escura."""
    hl_w = hl_w or balanced(hl_size, colw)
    lh = logo_h(logo_w)
    hb = block(S["headline"]["text"], dict(S["headline"]["style"]), hl_size, hl_w)
    sb = block(S["selo"]["text"], dict(S["selo"]["style"]), selo_size, colw)
    total = lh + gap_logo + hb["h"] + gap_txt + sb["h"]
    y = band_top + (band_bot - band_top - total) / 2
    if align == "center":
        lx = colx + (colw - logo_w) / 2
        hx = colx + (colw - hl_w) / 2
    else:
        lx = colx; hx = colx
    els = [logo_el(lx, y, logo_w)]
    y += lh + gap_logo
    els.append(text_el("headline", hx, y, hl_w, hl_size, align)); y += hb["h"] + gap_txt
    els.append(text_el("selo", colx, y, colw, selo_size, align))
    return els


def balanced(size, maxw):
    """largura de caixa que quebra o titulo em linhas equilibradas (sem viuva), com folga segura."""
    st = dict(S["headline"]["style"])
    one = width(S["headline"]["text"], st, size)
    if one + 12 <= maxw:
        return maxw
    best = maxw
    for wv in range(int(maxw), int(one / 2), -2):
        b = block(S["headline"]["text"], st, size, wv)
        if len(b["lines"]) > 2: break
        if b["margin"] >= 8 and len(b["lines"]) == 2:
            best = wv
    # devolve a menor largura de 2 linhas, mais uma folga
    return min(maxw, best + 10)


def side(F, logo_x, logo_w, colx, colw, hl_size, selo_size, band_top, band_bot, gap_txt):
    """como a peca-mestra: logo a esquerda, titulo+selo a direita, na faixa escura."""
    W, H = F["width"], F["height"]
    hl_w = balanced(hl_size, colw)
    hb = block(S["headline"]["text"], dict(S["headline"]["style"]), hl_size, hl_w)
    sb = block(S["selo"]["text"], dict(S["selo"]["style"]), selo_size, colw)
    total = hb["h"] + gap_txt + sb["h"]
    y = band_top + (band_bot - band_top - total) / 2
    hl = text_el("headline", colx, y, hl_w, hl_size)
    sl = text_el("selo", colx, y + hb["h"] + gap_txt, colw, selo_size)
    # logo: centro vertical um pouco abaixo do centro do titulo (como na mestra), sem inverter a leitura
    lh = logo_h(logo_w)
    hl_yc = y + hb["h"] / 2
    delta = 0.6 * ((colx + hb["w"] / 2) - (logo_x + logo_w / 2)) / W * H / 10
    yc = min(y + total / 2, hl_yc + delta)
    ly = yc - lh / 2
    return [logo_el(logo_x, ly, logo_w), hl, sl]


def make(fk):
    F = FMT[fk]; W, H, M = F["width"], F["height"], F["margin"]
    st, sr, sb_, sl = F["safe"]
    if fk == "email_600x1200":
        hero = hero_el(0, 0, 600, 560, cx=0.38)
        els = vstack(F, W, H, 560, 200, 46, 21, "left", 48, 504, 560, H - M, 48, 20)
    elif fk == "post_1080x1350":
        hero = hero_el(0, 0, 1080, 780, cx=0.42)
        els = side(F, 72, 250, 384, 636, 60, 28, 780, H - 20, 22)
    elif fk == "card_1080x1080":
        hero = hero_el(0, 0, 1080, 620, cx=0.43)
        els = side(F, 72, 240, 370, 650, 54, 27, 620, H - 10, 20)
    elif fk == "stories_1080x1920":
        hero = hero_el(0, 0, 1080, 920, cx=0.355)
        els = vstack(F, W, H, 1000, 330, 76, 36, "center", M, W - 2 * M, 920, H - M - sb_, 60, 30)
    elif fk == "banner_970x250":
        hero = hero_el(0, 0, 390, 250, cx=0.40)
        els = side(F, 420, 140, 600, 354, 30, 16, 0, 250, 10)
    else:
        raise SystemExit(fk)
    return hero, els


# ------------------------------------------------------------------ autocritica (previsao das regras)
def inter(a, b):
    x, y = max(a[0], b[0]), max(a[1], b[1])
    X, Y = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    return (X - x) * (Y - y) if X > x and Y > y else 0


def critique(fk, cand):
    F = FMT[fk]; W, H, M = F["width"], F["height"], F["margin"]
    safe = (M + F["safe"][3], M + F["safe"][0], W - 2 * M - F["safe"][1] - F["safe"][3], H - 2 * M - F["safe"][0] - F["safe"][2])
    by = {e["id"]: e for e in cand["elements"]}
    ext = {}
    msgs = []
    for e in cand["elements"]:
        g = e["geometry"]; b = (g["x"], g["y"], g["width"], g["height"])
        if e["type"] == "TEXT":
            p = e["_pred"]; m = (p["x"], p["y"], p["w"], p["h"]); ext[e["id"]] = m
            if m[1] + m[3] > b[1] + b[3] + 1.5 or m[0] + m[2] > b[0] + b[2] + 1.5: msgs.append(f"{e['id']} estouro previsto")
            if not (m[0] >= safe[0] - 1 and m[1] >= safe[1] - 1 and m[0] + m[2] <= safe[0] + safe[2] + 1 and m[1] + m[3] <= safe[1] + safe[3] + 1):
                msgs.append(f"{e['id']} fora da area segura {m} {safe}")
            if e["style"]["size"] < F["min_font"][e["role"]]: msgs.append(f"{e['id']} corpo abaixo do minimo")
            if p["margin"] < 6: msgs.append(f"{e['id']} quebra arriscada (folga {p['margin']:.1f}px)")
        else:
            ext[e["id"]] = b
        if b[0] < -0.5 or b[1] < -0.5 or b[0] + b[2] > W + 0.5 or b[1] + b[3] > H + 0.5: msgs.append(f"{e['id']} sai do canvas")
    lg = by["logo"]["geometry"]
    if lg["width"] < F["logo_min_width"]["otium"]: msgs.append("logo pequeno")
    lb = (lg["x"], lg["y"], lg["width"], lg["height"])
    if not (lb[0] >= safe[0] - 1 and lb[1] >= safe[1] - 1 and lb[0] + lb[2] <= safe[0] + safe[2] + 1 and lb[1] + lb[3] <= safe[1] + safe[3] + 1):
        msgs.append("logo fora da area segura")
    hg = by["hero"]["geometry"]; hb = (hg["x"], hg["y"], hg["width"], hg["height"])
    for t in ("headline", "selo"):
        if inter(ext[t], hb) > 4: msgs.append(f"{t} sobre a foto")
        if inter(ext[t], lb) > 4: msgs.append(f"{t} encosta no logo")
    if inter(ext["headline"], ext["selo"]) > 4: msgs.append("textos sobrepostos")
    if by["hero"]["_upscale"] > 1.5: msgs.append(f"aviso: ampliacao {by['hero']['_upscale']:.2f}x")
    # alinhamento quase-coincidente
    edges = [[b[0], b[0] + b[2] / 2, b[0] + b[2]] for b in (ext["logo"], ext["headline"], ext["selo"])]
    near = 0
    for i in range(3):
        for j in range(i + 1, 3):
            for k in range(3):
                d = abs(edges[i][k] - edges[j][k])
                if 2 < d < 0.02 * W: near += 1
    if near: msgs.append(f"{near} quase-alinhamentos {[[round(v) for v in e] for e in edges]}")
    # relacoes de tamanho (titulo > logo > selo, como na mestra)
    ar = {k: ext[k][2] * ext[k][3] for k in ("logo", "headline", "selo")}
    msgs.append("areas " + " ".join(f"{k}={v/1000:.1f}k" for k, v in ar.items()))
    if not ar["headline"] > 1.2 * ar["logo"]: msgs.append(f"size_rel titulo/logo {ar['headline']/ar['logo']:.2f}")
    if not ar["logo"] > 1.2 * ar["selo"]: msgs.append(f"size_rel logo/selo {ar['logo']/ar['selo']:.2f}")
    # ordem de leitura: logo antes do titulo
    o = lambda b: (b[1] + b[3] / 2) / H * 10 + (b[0] + b[2] / 2) / W
    if not o(lb) < o((by["headline"]["geometry"]["x"], by["headline"]["geometry"]["y"], by["headline"]["geometry"]["width"], by["headline"]["geometry"]["height"])):
        msgs.append("ordem de leitura invertida")
    return msgs


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1:] or list(FMT.keys())
    for fk in only:
        hero, els = make(fk)
        cand = {"schema_version": "bancada-0.1", "layout_id": L, "brand": src["brand"], "_format": fk,
                "canvas": {"width": FMT[fk]["width"], "height": FMT[fk]["height"], "background": src["canvas"]["background"]},
                "elements": [hero] + els, "relations": src["relations"], "groups": src["groups"], "text_over_image": []}
        msgs = critique(fk, cand)
        info = {e["id"]: e["_pred"]["lines"] for e in els if e["type"] == "TEXT"}
        for e in cand["elements"]:
            e.pop("_pred", None); e.pop("_upscale", None)
        json.dump(cand, open(os.path.join(OUT, f"{L}__{fk}.json"), "w"), ensure_ascii=False, indent=1)
        print(fk, "OK" if not msgs else msgs, info)


if __name__ == "__main__":
    main()
