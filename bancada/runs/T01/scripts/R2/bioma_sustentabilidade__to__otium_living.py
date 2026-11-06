#!/usr/bin/env python3
"""R2 — script de desdobramento escrito para a peça bioma_sustentabilidade.

Lê a peça-mestra, os formatos e os ativos; aplica regras de layout próprias por formato
(medição de texto com PIL nas mesmas fontes do render) e grava os 5 candidatos.
Opcional: --preview DIR grava uma prévia PIL aproximada de cada formato.
"""
import json, math, os, sys, copy
from PIL import ImageFont, Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
P = lambda *a: os.path.join(ROOT, *a)
LAYOUT = "otium_living"
ARM = "R2"
OUT = P("runs", "T01", "candidates", ARM)

SRC = json.load(open(P("fixtures", LAYOUT + ".json")))
FMTS = json.load(open(P("fixtures", "formats.json")))
ASSETS = json.load(open(P("assets", "assets.json")))
BY = {e["id"]: e for e in SRC["elements"]}

FONT_FILES = {
    ("Cormorant Garamond", 600): P("fonts", "CormorantGaramond-600.ttf"),
    ("Barlow", 600): P("fonts", "Barlow-600.ttf"),
    ("Inter", 400): "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
}
_fc = {}


def font(style, size):
    k = (style["font"], int(style["weight"]), size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONT_FILES[(k[0], k[1])], size)
    return _fc[k]


def wrap(text, style, size, width):
    """Quebra gulosa por espaço (como o navegador). Retorna linhas e larguras."""
    f = font(style, size)
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        t = w if not cur else cur + " " + w
        if cur and f.getlength(t) > width:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    return lines, [f.getlength(l) for l in lines]


def text_block(style, size, width, lh=None):
    """Mede o texto: nº de linhas, largura real, altura de caixa segura e deslocamento do 1º glifo."""
    lh = lh or style["line_height"]
    return lambda text: _measure(text, style, size, width, lh)


def _measure(text, style, size, width, lh):
    lines, ws = wrap(text, style, size, width)
    f = font(style, size)
    asc, desc = f.getmetrics()
    content = asc + desc
    L = size * lh
    over = max(0.0, (content - L) / 2)  # área de conteúdo que vaza da linha (acima e abaixo)
    # risco de quebra diferente no navegador: linha muito colada no limite
    # risco de o navegador quebrar diferente: linha colada no limite, ou próxima palavra quase cabendo
    tol = max(2.5, 0.004 * width)
    words = [l.split(" ") for l in lines]
    tight = max(ws) > width - tol
    for i in range(len(lines) - 1):
        if f.getlength(lines[i] + " " + words[i + 1][0]) < width + tol:
            tight = True
    h = len(lines) * L + over
    return {"lines": lines, "n": len(lines), "w": max(ws), "h": h, "over": over, "L": L, "tight": tight}


def balanced(text, style, s, width, lh):
    """Entre as larguras que mantêm o nº de linhas, escolhe a quebra mais equilibrada,
    evitando linha que comece com palavra de uma letra (ex.: "é" solto no início)."""
    m0 = _measure(text, style, s, width, lh)
    best, bcost = None, 1e9
    for w in range(int(width), int(width * 0.5), -2):
        m = _measure(text, style, s, w + 14, lh)
        if m["n"] > m0["n"]:
            break
        if m["tight"]:
            continue
        cost = m["w"] + sum(400 for l in m["lines"][1:] if len(l.split(" ")[0]) == 1)
        if cost < bcost - 0.5:
            best, bcost = m, cost
            best["box_w"] = w + 14
    if best is None:
        best = m0
        best["box_w"] = width
    return best


def fit_size(text, style, width, max_lines, smax, smin, lh=None):
    for s in range(smax, smin - 1, -1):
        m = _measure(text, style, s, width, lh or style["line_height"])
        if m["n"] <= max_lines and not m["tight"]:
            if m["n"] > 1:
                m = balanced(text, style, s, width, lh or style["line_height"])
            return s, m
    s = smin
    return s, _measure(text, style, s, width, lh or style["line_height"])


def vis_h(m):
    return m["n"] * m["L"] + 2 * m["over"]


def T(eid, x, y, w, size, m, align="left", z=None, slack=6):
    s = BY[eid]
    e = copy.deepcopy(s)
    e["style"]["size"] = size
    e["style"]["align"] = align
    # y = topo visual desejado; o glifo vaza 'over' px acima da caixa, então a caixa desce esse valor.
    by = y + m["over"]
    e["geometry"] = {"x": round(x, 2), "y": round(by, 2), "width": round(w, 2),
                     "height": math.ceil(m["h"] + slack), "z": z if z is not None else s["geometry"]["z"]}
    return e


def I(eid, x, y, w, h, crop=None, z=None):
    s = BY[eid]
    e = copy.deepcopy(s)
    e["geometry"] = {"x": round(x, 2), "y": round(y, 2), "width": round(w, 2), "height": round(h, 2),
                     "z": z if z is not None else s["geometry"]["z"]}
    if crop is not None:
        e["crop"] = [round(c, 5) for c in crop]
    return e


def hero_crop(bw, bh, ch=None, fy=None):
    """Janela sem distorção que mantém o prédio (área protegida) inteiro e centrado."""
    a = ASSETS["bioma_fachada"]
    px, py, pw, ph = a["protected"]
    ar_box = bw / bh
    k = a["height"] / a["width"]
    # cw = ar_box * ch * (H/W)
    if ch is None:
        ch = min(1.0, 1.0 / (ar_box * k))  # maior janela possível
    cw = ar_box * ch * k
    if cw > 1:
        cw = 1.0
        ch = cw / (ar_box * k)
    cx = px + pw / 2 - cw / 2
    cx = max(0.0, min(1 - cw, cx))
    if fy is None:
        fy = py + ph / 2
    cy = max(0.0, min(1 - ch, fy - ch / 2))
    return [cx, cy, cw, ch]


LOGO_AR = ASSETS["bioma_logo"]["width"] / ASSETS["bioma_logo"]["height"]


def logo(x, y, w):
    return I("logo", x, y, w, w / LOGO_AR, [0, 0, 1, 1])


def legal_block(width, size):
    """Jurídico: estreita a caixa alguns px até a quebra ficar estável (sem linha no limite)."""
    w = width
    while True:
        m = _measure(BY["legal"]["text"], BY["legal"]["style"], size, w, BY["legal"]["style"]["line_height"])
        if not m["tight"] or w < width - 40:
            m["box_w"] = w
            return m
        w -= 1


ATTRS = [("icon_solar", "lbl_solar"), ("icon_chuva", "lbl_chuva"), ("icon_coleta", "lbl_coleta")]
LBL_STYLE = BY["lbl_solar"]["style"]
HL = BY["headline"]


def attrs_columns(x0, y, total_w, ncol_gap, icon, lsize, label_gap=16, lh=None):
    """3 colunas: ícone em cima, rótulo embaixo, alinhados à esquerda da coluna."""
    cw = (total_w - 2 * ncol_gap) / 3
    els, bottom = [], y
    for i, (ic, lb) in enumerate(ATTRS):
        cx = x0 + i * (cw + ncol_gap)
        els.append(I(ic, cx, y, icon, icon))
        m = _measure(BY[lb]["text"], LBL_STYLE, lsize, cw, lh or LBL_STYLE["line_height"])
        ty = y + icon + label_gap
        els.append(T(lb, cx, ty, cw, lsize, m))
        bottom = max(bottom, ty + vis_h(m))
    return els, bottom


def attrs_rows(x0, y, total_w, icon, lsize, gap_x, row_gap):
    """3 linhas: ícone à esquerda e rótulo centrado verticalmente ao lado."""
    els = []
    lw = total_w - icon - gap_x
    for i, (ic, lb) in enumerate(ATTRS):
        ry = y + i * (icon + row_gap)
        els.append(I(ic, x0, ry, icon, icon))
        m = _measure(BY[lb]["text"], LBL_STYLE, lsize, lw, LBL_STYLE["line_height"])
        ty = ry + (icon - vis_h(m)) / 2  # centra a extensão visual no ícone
        els.append(T(lb, x0 + icon + gap_x, ty, lw, lsize, m))
    return els, y + 3 * icon + 2 * row_gap


def attrs_inline(x0, y, total_w, icon, lsize, gap_x, col_gap):
    """3 colunas estilo peça-mestra: ícone à esquerda, rótulo à direita."""
    cw = (total_w - 2 * col_gap) / 3
    lw = cw - icon - gap_x
    els, bottom = [], y + icon
    for i, (ic, lb) in enumerate(ATTRS):
        cx = x0 + i * (cw + col_gap)
        els.append(I(ic, cx, y, icon, icon))
        m = _measure(BY[lb]["text"], LBL_STYLE, lsize, lw, LBL_STYLE["line_height"])
        ty = y + (icon - vis_h(m)) / 2
        els.append(T(lb, cx + icon + gap_x, ty, lw, lsize, m))
        bottom = max(bottom, ty + vis_h(m))
    return els, bottom


# --------------------------------------------------------------------------- formatos
def stack(y0, y1, blocks, weights):
    """Empilha blocos (altura, builder(y)) entre y0 e y1 distribuindo o espaço livre nos vãos."""
    free = y1 - y0 - sum(h for h, _ in blocks)
    tw = sum(weights)
    els, y = [], y0
    for i, (h, fn) in enumerate(blocks):
        y += free * weights[i] / tw
        els += fn(y)
        y += h
    return els, free


def headline_row(x0, cw, lg_w, gap, smax, smin, lines=2):
    """Título à esquerda e logo à direita, centrado na altura do título (como na peça-mestra)."""
    hw = cw - lg_w - gap
    hs, hm = fit_size(HL["text"], HL["style"], hw, lines, smax, smin)
    hv = vis_h(hm)
    lh_ = lg_w / LOGO_AR
    H = max(hv, lh_)

    def build(y):
        return [T("headline", x0, y + (H - hv) / 2, hm.get("box_w", hw), hs, hm),
                logo(x0 + cw - lg_w, y + (H - lh_) / 2, lg_w)]
    return H, build


def columns_block(x0, cw, gap, icon, lsize, lgap):
    _, b = attrs_columns(x0, 0, cw, gap, icon, lsize, lgap)
    return b, (lambda y: attrs_columns(x0, y, cw, gap, icon, lsize, lgap)[0])


def legal_at(x0, bottom, cw, size):
    lm = legal_block(cw, size)
    return T("legal", x0, bottom - vis_h(lm), lm["box_w"], size, lm), bottom - vis_h(lm)


def email():
    F = FMTS["email_600x1200"]; W, H, M = F["width"], F["height"], F["margin"]
    cw = W - 2 * M
    hero_h = 450
    els = [I("hero", 0, 0, W, hero_h, hero_crop(W, hero_h))]
    lg, legal_y = legal_at(M, H - M - 4, cw, 10)
    hs, hm = fit_size(HL["text"], HL["style"], cw, 2, 46, 40)
    icon, lsz, rg = 68, 20, 18
    lg_w = 150
    blocks = [
        (vis_h(hm), lambda y: [T("headline", M, y, hm.get("box_w", cw), hs, hm)]),
        (3 * icon + 2 * rg, lambda y: attrs_rows(M, y, cw, icon, lsz, 18, rg)[0]),
        (lg_w / LOGO_AR, lambda y: [logo(M, y, lg_w)]),
    ]
    e, free = stack(hero_h, legal_y, blocks + [(0, lambda y: [])], [1.0, 0.9, 1.0, 0.8])
    return W, H, els + e + [lg]


def post():
    F = FMTS["post_1080x1350"]; W, H, M = F["width"], F["height"], F["margin"]
    cw = W - 2 * M
    hero_h = 620
    els = [I("hero", 0, 0, W, hero_h, hero_crop(W, hero_h, ch=0.9))]
    lg, legal_y = legal_at(M, H - M - 4, cw, 14)
    blocks = [headline_row(M, cw, 230, 50, 76, 56), columns_block(M, cw, 36, 100, 26, 18)]
    e, _ = stack(hero_h, legal_y, blocks + [(0, lambda y: [])], [1, 0.9, 1])
    return W, H, els + e + [lg]


def card():
    F = FMTS["card_1080x1080"]; W, H, M = F["width"], F["height"], F["margin"]
    cw = W - 2 * M
    hero_h = 410
    els = [I("hero", 0, 0, W, hero_h, hero_crop(W, hero_h))]
    lg, legal_y = legal_at(M, H - M - 4, cw, 14)
    blocks = [headline_row(M, cw, 210, 50, 66, 50), columns_block(M, cw, 36, 84, 24, 16)]
    e, _ = stack(hero_h, legal_y, blocks + [(0, lambda y: [])], [1, 0.85, 1])
    return W, H, els + e + [lg]


def stories():
    F = FMTS["stories_1080x1920"]; W, H, M = F["width"], F["height"], F["margin"]
    sx0, sy0 = M + F["safe"][3], M + F["safe"][0]
    sx1, sy1 = W - M - F["safe"][1], H - M - F["safe"][2]
    cw = sx1 - sx0
    hero_h = 840
    els = [I("hero", 0, 0, W, hero_h, hero_crop(W, hero_h))]
    lg, legal_y = legal_at(sx0, sy1 - 4, cw, 16)
    blocks = [headline_row(sx0, cw, 240, 40, 80, 60), columns_block(sx0, cw, 36, 108, 28, 18)]
    e, _ = stack(hero_h, legal_y, blocks + [(0, lambda y: [])], [1, 0.85, 1])
    return W, H, els + e + [lg]


def banner():
    F = FMTS["banner_970x250"]; W, H, M = F["width"], F["height"], F["margin"]
    hero_w = 236
    els = [I("hero", 0, 0, hero_w, H, hero_crop(hero_w, H))]
    x0 = hero_w + 22
    lg_w = 132
    lgx = W - M - 2 - lg_w
    tw = lgx - 22 - x0
    # jurídico ocupa toda a largura de texto embaixo (inclusive sob o logo)
    lg, legal_y = legal_at(x0, H - M - 3, W - M - x0, 8)
    hs, hm = fit_size(HL["text"], HL["style"], tw, 1, 34, 24)
    # atributos: colunas com a largura natural de 2 linhas de cada rótulo
    icon, gx, lsz = 32, 7, 13
    widths = []
    for ic, lb in ATTRS:
        for w in range(60, 300):
            m = _measure(BY[lb]["text"], LBL_STYLE, lsz, w, LBL_STYLE["line_height"])
            if m["n"] <= 2 and not m["tight"]:
                break
        widths.append(w + 8)
    used = sum(icon + gx + w for w in widths)
    cgap = (tw - used) / 2
    mrow = [_measure(BY[lb]["text"], LBL_STYLE, lsz, widths[i], LBL_STYLE["line_height"]) for i, (ic, lb) in enumerate(ATTRS)]
    row_h = max(icon, max(vis_h(m) for m in mrow))

    def attrs(y):
        out, x = [], x0
        for i, (ic, lb) in enumerate(ATTRS):
            out.append(I(ic, x, y + (row_h - icon) / 2, icon, icon))
            out.append(T(lb, x + icon + gx, y + (row_h - vis_h(mrow[i])) / 2, widths[i], lsz, mrow[i]))
            x += icon + gx + widths[i] + cgap
        return out
    blocks = [(vis_h(hm), lambda y: [T("headline", x0, y, tw, hs, hm)]), (row_h, attrs)]
    e, _ = stack(M, legal_y, blocks + [(0, lambda y: [])], [0.5, 1, 1])
    # logo centrado verticalmente na faixa título+atributos
    top = min(el["geometry"]["y"] for el in e if el["id"] == "headline") - hm["over"]
    bot = max(el["geometry"]["y"] + el["geometry"]["height"] for el in e if el["id"].startswith("icon"))
    lh_ = lg_w / LOGO_AR
    e.append(logo(lgx, (top + bot) / 2 - lh_ / 2, lg_w))
    return W, H, els + e + [lg]


BUILD = {"email_600x1200": email, "post_1080x1350": post, "card_1080x1080": card,
         "stories_1080x1920": stories, "banner_970x250": banner}


def preview(fmt, cand, d):
    W, H = cand["canvas"]["width"], cand["canvas"]["height"]
    im = Image.new("RGB", (W, H), cand["canvas"]["background"])
    dr = ImageDraw.Draw(im)
    for e in sorted(cand["elements"], key=lambda e: e["geometry"]["z"]):
        g = e["geometry"]
        if e["type"] == "IMAGE":
            a = ASSETS[e["asset"]]
            src = Image.open(P("assets", a["file"])).convert("RGBA")
            c = e["crop"]
            box = (c[0] * a["width"], c[1] * a["height"], (c[0] + c[2]) * a["width"], (c[1] + c[3]) * a["height"])
            t = src.crop(tuple(int(round(v)) for v in box)).resize((max(1, int(g["width"])), max(1, int(g["height"]))))
            im.paste(t, (int(g["x"]), int(g["y"])), t)
        else:
            s = e["style"]
            m = _measure(e["text"], s, s["size"], g["width"], s["line_height"])
            f = font(s, s["size"])
            for i, l in enumerate(m["lines"]):
                ly = g["y"] + i * m["L"] + (m["L"] - sum(f.getmetrics())) / 2
                dr.text((g["x"], ly), l, font=f, fill=s["color"])
            dr.rectangle([g["x"], g["y"], g["x"] + g["width"], g["y"] + g["height"]], outline="#ff00ff")
    im.save(os.path.join(d, f"{fmt}.png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    pv = None
    if "--preview" in sys.argv:
        pv = sys.argv[sys.argv.index("--preview") + 1]
        only = [a for a in only if a != pv]
        os.makedirs(pv, exist_ok=True)
    for fmt, fn in BUILD.items():
        if only and fmt not in only:
            continue
        W, H, els = fn()
        order = [e["id"] for e in SRC["elements"]]
        els.sort(key=lambda e: order.index(e["id"]) if e["id"] in order else 99)
        cand = {"schema_version": "bancada-0.1", "layout_id": LAYOUT, "brand": SRC["brand"], "_format": fmt,
                "canvas": {"width": W, "height": H, "background": SRC["canvas"]["background"]}, "elements": els}
        path = os.path.join(OUT, f"{LAYOUT}__{fmt}.json")
        json.dump(cand, open(path, "w"), ensure_ascii=False, indent=1)
        info = {e["id"]: (e["geometry"]["x"], e["geometry"]["y"], e["geometry"]["width"], e["geometry"]["height"],
                          e.get("style", {}).get("size")) for e in els}
        print(fmt, json.dumps(info))
        if pv:
            preview(fmt, cand, pv)


if __name__ == "__main__":
    main()
