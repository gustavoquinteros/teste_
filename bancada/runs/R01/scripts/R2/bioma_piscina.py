#!/usr/bin/env python3
"""R2 — script de layout proprio para a peca bioma_piscina (5 formatos).

Ideia de direcao de arte: a peca-mestra e "faixa verde translucida sobre a foto, texto em creme".
Nos formatos que nao sao 16:9 a foto inteira (predio + piscina) nao cabe atras do texto sem perder a
piscina, entao a composicao vira uma pilha editorial sobre o verde da marca:
  marca (logo + headline)  ->  foto sangrando nas laterais  ->  CTA + legal.
No card a marca fica lado a lado (logo | headline) para a foto sair inteira; no stories a foto vai
para o topo (por tras da UI de cima) e o texto fica dentro da area segura; no banner a foto vai
para a direita (como na mestra) e o texto ocupa o painel verde a esquerda.

Medicao de texto: PIL (larguras) + metricas hhea/OS2 lidas direto do TTF/OTF (altura do content-area,
que e o que o Chromium mede com Range.getClientRects).
"""
import json, os, struct, subprocess, sys
from PIL import ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
LAYOUT = "bioma_piscina"
OUT = os.path.join(ROOT, "runs", "R01", "candidates", "R2")
FORMATS = ["email_600x1200", "post_1080x1350", "card_1080x1080", "stories_1080x1920", "banner_970x250"]

src = json.load(open(os.path.join(ROOT, "fixtures", LAYOUT + ".json")))
fmts = json.load(open(os.path.join(ROOT, "fixtures", "formats.json")))
assets = json.load(open(os.path.join(ROOT, "assets", "assets.json")))
S = {e["id"]: e for e in src["elements"]}


# ------------------------------------------------------------------ fontes
def font_file(family, weight):
    if family == "Inter":
        return subprocess.check_output(["fc-match", f"Inter:weight={ {400: 80, 600: 200}.get(weight, 80) }", "--format=%{file}"]).decode()
    return os.path.join(ROOT, "fonts", f"{family.replace(' ', '')}-{weight}.ttf")


def vmetrics(path):
    """(ascent, descent) em unidades/upem como o Skia/FreeType usa (hhea; typo se USE_TYPO_METRICS)."""
    d = open(path, "rb").read()
    n = struct.unpack(">H", d[4:6])[0]
    tabs = {}
    for i in range(n):
        tag, _, off, ln = struct.unpack(">4sIII", d[12 + 16 * i: 28 + 16 * i])
        tabs[tag.decode()] = off
    upem = struct.unpack(">H", d[tabs["head"] + 18: tabs["head"] + 20])[0]
    h = tabs["hhea"]
    asc, desc = struct.unpack(">hh", d[h + 4: h + 8])
    o = tabs.get("OS/2")
    if o is not None:
        fs_sel = struct.unpack(">H", d[o + 62: o + 64])[0]
        tasc, tdesc = struct.unpack(">hh", d[o + 68: o + 72])
        wasc, wdesc = struct.unpack(">HH", d[o + 74: o + 78])
        if fs_sel & (1 << 7):
            asc, desc = tasc, tdesc
        if asc == 0 and desc == 0:
            asc, desc = wasc, -wdesc
    return asc / upem, -desc / upem


_fcache = {}


def font(style):
    key = (style["font"], int(style["weight"]), round(style["size"], 2))
    if key not in _fcache:
        p = font_file(style["font"], int(style["weight"]))
        _fcache[key] = (ImageFont.truetype(p, size=style["size"]), vmetrics(p))
    return _fcache[key]


def wrap(text, style, width):
    f, _ = font(style)
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        t = w if not cur else cur + " " + w
        if f.getlength(t) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def block(text, style, width):
    """altura de caixa segura + extensao vertical que o Chromium vai medir."""
    f, (a, d) = font(style)
    lines = wrap(text, style, width)
    n = len(lines)
    size = style["size"]
    lh = size * style["line_height"]
    content = round(a * size) + round(d * size)
    top_over = max(0.0, (content - lh) / 2)  # quanto o glifo sobe acima da caixa
    bottom = (n - 1) * lh + (lh + content) / 2
    wmax = max(f.getlength(l) for l in lines)
    return {"lines": lines, "n": n, "lh": lh, "content": content, "top_over": top_over,
            "box_h": int(bottom + 4), "ext_bottom": bottom, "w": wmax}


def robust_width(text, style, max_w, n_target=None):
    """menor largura (<= max_w) cujo quebrar de linhas e estavel a +-3% e usa o menor n de linhas
    possivel em max_w (ou n_target): linhas equilibradas, como um DA quebraria."""
    n_best = n_target or block(text, style, max_w * 0.96)["n"]
    lo, hi = 10, max_w
    for _ in range(40):
        mid = (lo + hi) / 2
        if block(text, style, mid)["n"] <= n_best:
            hi = mid
        else:
            lo = mid
    w = min(max_w, hi * 1.045 + 2)
    ref = block(text, style, w)["lines"]
    # estabilidade: a 0.97w e 1.03w (limitado a max_w) as linhas nao mudam
    for k in (0.965, 1.03):
        if block(text, style, min(max_w, w * k))["lines"] != ref:
            return max_w, block(text, style, max_w)
    return w, block(text, style, w)


# ------------------------------------------------------------------ elementos
def text_el(id_, x, y, w, style_over, blk):
    s = S[id_]
    st = dict(s["style"])
    st.update(style_over)
    return {"id": id_, "type": "TEXT", "role": s["role"], "priority": s["priority"], "text": s["text"],
            "geometry": {"x": round(x, 1), "y": round(y, 1), "width": round(w, 1), "height": blk["box_h"], "z": 5},
            "style": st}


A = assets["bioma_piscina"]
AR = A["width"] / A["height"]
LOGO = assets["bioma_logo"]
LOGO_AR = LOGO["width"] / LOGO["height"]


def hero_el(x, y, w, h, crop):
    return {"id": "hero", "type": "IMAGE", "role": "HERO", "priority": 0.9, "asset": "bioma_piscina",
            "geometry": {"x": x, "y": y, "width": w, "height": h, "z": 1}, "crop": [round(c, 5) for c in crop]}


def hero_crop(bw, bh, keep_top=0.035, keep_bot=0.95):
    """janela sem distorcao; prioriza largura toda (piscina, x 0.1-0.9) e corta ceu antes de corte lateral."""
    arB = bw / bh
    cw = 1.0
    ch = cw * AR / arB
    if ch > 1:
        ch = 1.0
        cw = arB / AR
    cx = (1 - cw) / 2
    # vertical: mantem a base da piscina (0.92) e o maximo do predio (topo 0.05)
    y0 = min(max(0.0, keep_bot - ch), 1 - ch)
    if ch >= keep_bot - keep_top:
        y0 = max(0.0, min(keep_top - (ch - (keep_bot - keep_top)) / 2, 1 - ch))
    return [cx, y0, cw, ch]


def logo_el(x, y, w):
    h = w / LOGO_AR
    return {"id": "logo", "type": "IMAGE", "role": "LOGO", "priority": 0.7, "asset": "bioma_logo",
            "geometry": {"x": round(x, 1), "y": round(y, 1), "width": round(w, 1), "height": round(h, 2), "z": 6},
            "crop": [0, 0, 1, 1]}


def st(size, lh=None, align="left"):
    d = {"size": size, "align": align}
    if lh:
        d["line_height"] = lh
    return d


def style_of(id_, size, lh=None):
    s = dict(S[id_]["style"])
    s["size"] = size
    if lh:
        s["line_height"] = lh
    return s


# ------------------------------------------------------------------ layouts
def stack_vertical(fk, P):
    """logo / headline / foto (sangra lateral) / cta / legal, sobrando espaco -> respiros."""
    F = fmts[fk]
    W, H, m = F["width"], F["height"], F["margin"]
    tw = W - 2 * m
    hs = style_of("headline", P["h"], P.get("hlh", 1.05))
    cs = style_of("cta", P["c"])
    ls = style_of("legal", P["l"], P.get("llh", 1.3))
    hw, hb = robust_width(S["headline"]["text"], hs, tw)
    cw_, cb = robust_width(S["cta"]["text"], cs, tw)
    lb = block(S["legal"]["text"], ls, tw - 4)
    lw = tw
    logo_w = P["logo"]
    logo_h = logo_w / LOGO_AR
    # alturas visuais (extensao de glifo) para os respiros
    hv = hb["ext_bottom"] + hb["top_over"]
    cv = cb["ext_bottom"] + cb["top_over"]
    lv = lb["ext_bottom"] + lb["top_over"]
    g = P["gaps"]  # [logo-head, head-foto, foto-cta, cta-legal]
    fixed = m + logo_h + g[0] + hv + g[1] + g[2] + cv + g[3] + lv + m
    ph = H - fixed
    ph_max = W / (AR * P.get("min_cw", 0.86))  # foto mais alta que isso cortaria a piscina
    extra = max(0, ph - ph_max)
    ph = min(ph, ph_max)
    # distribui sobra: topo/base e respiros em volta da foto; logo+headline continuam colados (grupo)
    top_pad = m + extra * 0.25
    gi = [g[0], g[1] + extra * 0.25, g[2] + extra * 0.25, g[3]]
    y = top_pad
    els = [logo_el(m, y, logo_w)]
    y += logo_h + gi[0]
    els.append(text_el("headline", m, y + hb["top_over"], hw, st(P["h"], P.get("hlh", 1.05)), hb))
    y += hv + gi[1]
    ph = int(ph)
    els.append(hero_el(0, int(y), W, ph, hero_crop(W, ph)))
    y = int(y) + ph + gi[2]
    els.append(text_el("cta", m, y + cb["top_over"], cw_, st(P["c"]), cb))
    y += cv + gi[3]
    els.append(text_el("legal", m, y + lb["top_over"], lw, st(P["l"], P.get("llh", 1.3)), lb))
    return els


def card(fk, P):
    F = fmts[fk]
    W, H, m = F["width"], F["height"], F["margin"]
    tw = W - 2 * m
    logo_w = P["logo"]
    logo_h = logo_w / LOGO_AR
    hx = m + logo_w + P["col_gap"]
    hs = style_of("headline", P["h"], 1.05)
    hw, hb = robust_width(S["headline"]["text"], hs, W - m - hx)
    cs = style_of("cta", P["c"])
    cw_, cb = robust_width(S["cta"]["text"], cs, tw)
    ls = style_of("legal", P["l"], 1.3)
    lb = block(S["legal"]["text"], ls, tw - 4)
    hv = hb["ext_bottom"] + hb["top_over"]
    band = max(logo_h, hv)
    els = [logo_el(m, m + (band - logo_h) / 2, logo_w),
           text_el("headline", hx, m + (band - hv) / 2 + hb["top_over"], hw, st(P["h"], 1.05), hb)]
    lv = lb["ext_bottom"] + lb["top_over"]
    cv = cb["ext_bottom"] + cb["top_over"]
    ly = H - m - lv
    cy = ly - P["g_cl"] - cv
    py = m + band + P["g_top"]
    ph = int(cy - P["g_pc"] - py)
    els.append(hero_el(0, int(py), W, ph, hero_crop(W, ph)))
    els.append(text_el("cta", m, cy + cb["top_over"], cw_, st(P["c"]), cb))
    els.append(text_el("legal", m, ly + lb["top_over"], tw, st(P["l"], 1.3), lb))
    return els


def stories(fk, P):
    F = fmts[fk]
    W, H, m = F["width"], F["height"], F["margin"]
    sx, sy = m + F["safe"][3], m + F["safe"][0]
    sy1 = H - m - F["safe"][2]
    tw = W - 2 * m - F["safe"][1] - F["safe"][3]
    ph = int(W / (AR * P["cw"]))
    els = [hero_el(0, 0, W, ph, hero_crop(W, ph))]
    logo_w = P["logo"]
    logo_h = logo_w / LOGO_AR
    hs = style_of("headline", P["h"], 1.05)
    hw, hb = robust_width(S["headline"]["text"], hs, tw)
    cs = style_of("cta", P["c"])
    cw_, cb = robust_width(S["cta"]["text"], cs, tw)
    ls = style_of("legal", P["l"], 1.3)
    lb = block(S["legal"]["text"], ls, tw - 4)
    hv = hb["ext_bottom"] + hb["top_over"]
    cv = cb["ext_bottom"] + cb["top_over"]
    lv = lb["ext_bottom"] + lb["top_over"]
    g = P["gaps"]
    total = logo_h + g[0] + hv + g[1] + cv + g[2] + lv
    y0 = max(sy, ph + P["g_photo"])
    room = sy1 - y0
    extra = max(0, room - total)
    y = y0 + extra * 0.4
    gi = [g[0], g[1] + extra * 0.1, g[2] + extra * 0.1]
    els.append(logo_el(sx, y, logo_w))
    y += logo_h + gi[0]
    els.append(text_el("headline", sx, y + hb["top_over"], hw, st(P["h"], 1.05), hb))
    y += hv + gi[1]
    els.append(text_el("cta", sx, y + cb["top_over"], cw_, st(P["c"]), cb))
    y += cv + gi[2]
    els.append(text_el("legal", sx, y + lb["top_over"], tw, st(P["l"], 1.3), lb))
    if y + lv > sy1:
        print("  !! stories estourou a area segura", y + lv, sy1, file=sys.stderr)
    return els


def banner(fk, P):
    F = fmts[fk]
    W, H, m = F["width"], F["height"], F["margin"]
    pw = P["photo_w"]
    px = W - pw
    els = [hero_el(px, 0, pw, H, hero_crop(pw, H))]
    right = px - P["gutter"]
    logo_w = P["logo"]
    logo_h = logo_w / LOGO_AR
    hx = m + logo_w + P["col_gap"]
    hs = style_of("headline", P["h"], 1.05)
    hw, hb = robust_width(S["headline"]["text"], hs, right - hx)
    cs = style_of("cta", P["c"])
    cw_, cb = robust_width(S["cta"]["text"], cs, right - hx)
    ls = style_of("legal", P["l"], P.get("llh", 1.3))
    lwid = P.get("legal_w", right - m)
    lb = block(S["legal"]["text"], ls, lwid - 4)
    hv = hb["ext_bottom"] + hb["top_over"]
    cv = cb["ext_bottom"] + cb["top_over"]
    lv = lb["ext_bottom"] + lb["top_over"]
    top = m + P.get("top", 0)
    els.append(logo_el(m, top, logo_w))
    els.append(text_el("headline", hx, top + hb["top_over"], hw, st(P["h"], 1.05), hb))
    cy = top + hv + P["g_hc"]
    els.append(text_el("cta", hx, cy + cb["top_over"], cw_, st(P["c"]), cb))
    ly = H - m - lv
    els.append(text_el("legal", m, ly + lb["top_over"], lwid, st(P["l"], P.get("llh", 1.3)), lb))
    if cy + cv + 6 > ly:
        print("  !! banner: cta encosta no legal", cy + cv, ly, file=sys.stderr)
    return els


PARAMS = {
    "email_600x1200": (stack_vertical, {"logo": 180, "h": 55, "c": 24, "l": 10, "llh": 1.4,
                                         "gaps": [34, 44, 40, 20], "min_cw": 0.86}),
    "post_1080x1350": (stack_vertical, {"logo": 230, "h": 70, "c": 32, "l": 14, "llh": 1.3,
                                         "gaps": [44, 48, 44, 22], "min_cw": 0.86}),
    "card_1080x1080": (card, {"logo": 210, "col_gap": 60, "h": 68, "c": 30, "l": 14,
                              "g_top": 44, "g_pc": 36, "g_cl": 16}),
    "stories_1080x1920": (stories, {"cw": 0.88, "g_photo": 64, "logo": 280, "h": 86, "c": 38, "l": 17,
                                    "gaps": [44, 48, 30]}),
    "banner_970x250": (banner, {"photo_w": 430, "gutter": 20, "logo": 130, "col_gap": 20, "h": 41, "c": 16, "legal_w": 470,
                                "l": 8, "llh": 1.3, "g_hc": 10, "top": 2}),
}


# ------------------------------------------------------------------ diagnostico (estimativa local)
def diag(fk, els):
    F = fmts[fk]
    W, H = F["width"], F["height"]
    ext = {}
    for e in els:
        g = e["geometry"]
        if e["type"] == "TEXT":
            b = block(e["text"], e["style"], g["width"])
            ext[e["id"]] = (g["x"], g["y"] - b["top_over"], b["w"], b["ext_bottom"] + b["top_over"])
        else:
            ext[e["id"]] = (g["x"], g["y"], g["width"], g["height"])
    srcA = {"hero": 1920 * 1080, "logo": 260 * 131, "headline": 600 * 150, "cta": 470 * 35, "legal": 680 * 80}
    ids = ["hero", "logo", "headline", "cta", "legal"]
    rel = lambda a, b: 1 if a > b * 1.2 else (-1 if a < b / 1.2 else 0)
    ok = tot = 0
    for i in range(5):
        for j in range(i + 1, 5):
            tot += 1
            ca = ext[ids[i]][2] * ext[ids[i]][3]
            cb = ext[ids[j]][2] * ext[ids[j]][3]
            ok += rel(srcA[ids[i]], srcA[ids[j]]) == rel(ca, cb)
    edges = [(x, x + w / 2, x + w) for k, (x, y, w, h) in ext.items() if k != "hero"]
    near = sum(1 for i in range(len(edges)) for j in range(i + 1, len(edges)) for k in range(3)
               if 2 < abs(edges[i][k] - edges[j][k]) < 0.02 * W)
    print(f"  {fk}: size_rel~{ok}/{tot} near_align={near}")
    for k, v in ext.items():
        print("    ", k, [round(t, 1) for t in v], "crop" if k == "hero" else "",
              next(e for e in els if e["id"] == k).get("crop", ""))


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1:] or FORMATS
    for fk in only:
        fn, P = PARAMS[fk]
        els = fn(fk, P)
        F = fmts[fk]
        cand = {"schema_version": "bancada-0.1", "layout_id": LAYOUT, "brand": src["brand"], "_format": fk,
                "canvas": {"width": F["width"], "height": F["height"], "background": src["canvas"]["background"]},
                "elements": els, "relations": src["relations"], "groups": src["groups"],
                "_provenance": "R2: script de layout proprio (runs/R01/scripts/R2/bioma_piscina.py)"}
        json.dump(cand, open(os.path.join(OUT, f"{LAYOUT}__{fk}.json"), "w"), ensure_ascii=False, indent=1)
        diag(fk, els)


if __name__ == "__main__":
    main()
