"""Gera logos e as 6 pecas-mestras (KV 16:9, 1920x1080) em Layout IR, mais a tabela de formatos.

Modelo de dados segue o Kernel V0 do Semantic Layout Harness (set/2026), simplificado:
elementos com type/role/priority/content/geometry/style, relacoes e grupos.
Textos e texto legal do Bioma vem do briefing real (BIOMA | CCN, out/2026).
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")
F = os.path.join(ROOT, "fonts")
FX = os.path.join(ROOT, "fixtures")


def logo(aid, word, sub, font_word, font_sub, fg, accent):
    W, H = 900, 360
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fw = ImageFont.truetype(os.path.join(F, font_word), 210)
    fs = ImageFont.truetype(os.path.join(F, font_sub), 54)
    bw = d.textbbox((0, 0), word, font=fw)
    d.text(((W - (bw[2] - bw[0])) / 2 - bw[0], 10 - bw[1] + 20), word, font=fw, fill=fg)
    d.line([(W * 0.18, 262), (W * 0.82, 262)], fill=accent, width=6)
    bs = d.textbbox((0, 0), sub, font=fs)
    d.text(((W - (bs[2] - bs[0])) / 2 - bs[0], 282 - bs[1]), sub, font=fs, fill=fg)
    im = im.crop(im.getbbox())
    im.save(os.path.join(A, aid + ".png"))
    return im.size


LEGAL_BIOMA = ("Material com imagens e informações sujeitas a alterações. (1) Empreendimento em processo de "
               "Certificação EDGE. (2) Torres residenciais com previsão para futura instalação de sistema de "
               "aquecimento solar. (3) Torres residenciais com sistema de reaproveitamento de água das chuvas, "
               "para irrigação dos jardins das áreas comuns. (4) Paisagismo com plantio de árvores nativas, "
               "minimizando a necessidade de irrigação. (5) Torres residenciais com espaço e infraestrutura para "
               "três pontos de recarga de veículos elétricos. (*) Diferenciais sustentáveis do setor residencial.")

BIOMA = {"bg": "#1E3B2C", "title": "Cormorant Garamond", "support": "Barlow", "text": "Inter",
         "cream": "#F1E9D6", "light": "#B9CBA4", "accent": "#C0392B"}
OTIUM = {"bg": "#2B2A2D", "title": "Archivo", "support": "Host Grotesk", "text": "Poppins",
         "cream": "#F4EDE4", "light": "#D9A27A", "accent": "#D9A27A"}


def T(id, role, pr, text, x, y, w, h, font, size, weight, color, align="left", lh=1.15, z=5):
    return {"id": id, "type": "TEXT", "role": role, "priority": pr, "text": text,
            "geometry": {"x": x, "y": y, "width": w, "height": h, "z": z},
            "style": {"font": font, "size": size, "weight": weight, "line_height": lh, "color": color, "align": align}}


def I(id, role, pr, asset, x, y, w, h, crop, z=1):
    return {"id": id, "type": "IMAGE", "role": role, "priority": pr, "asset": asset,
            "geometry": {"x": x, "y": y, "width": w, "height": h, "z": z}, "crop": crop}


def S(id, x, y, w, h, color, opacity=1.0, z=2):
    return {"id": id, "type": "SHAPE", "role": "DECOR", "priority": 0.1,
            "geometry": {"x": x, "y": y, "width": w, "height": h, "z": z},
            "style": {"color": color, "opacity": opacity}}


def crop_for(asset, bw, bh, focus=(0.5, 0.5)):
    """Janela normalizada que cobre a caixa sem distorcer, centrada em focus."""
    aw, ah = asset["width"], asset["height"]
    ar_box, ar_img = bw / bh, aw / ah
    if ar_img > ar_box:  # imagem mais larga: corta laterais
        cw, ch = ar_box / ar_img, 1.0
    else:
        cw, ch = 1.0, ar_img / ar_box
    cx = min(max(focus[0] - cw / 2, 0), 1 - cw)
    cy = min(max(focus[1] - ch / 2, 0), 1 - ch)
    return [round(cx, 4), round(cy, 4), round(cw, 4), round(ch, 4)]


def main():
    man = json.load(open(os.path.join(A, "assets.json")))
    for aid, args in (("bioma_logo", ("bioma", "Cidade Center Norte", "CormorantGaramond-600.ttf", "Barlow-600.ttf", (241, 233, 214, 255), (192, 57, 43, 255))),
                      ("otium_logo", ("OTIUM", "por artefacto", "Archivo-700.ttf", "HostGrotesk-400.ttf", (244, 237, 228, 255), (217, 162, 122, 255)))):
        w, h = logo(aid, *args)
        man[aid] = {"file": aid + ".png", "width": w, "height": h, "protected": [0, 0, 1, 1], "kind": "logo", "real_size": [w, h]}
    json.dump(man, open(os.path.join(A, "assets.json"), "w"), indent=1)

    def lg(aid, wpx):
        a = man[aid]; return wpx, round(wpx * a["height"] / a["width"])

    os.makedirs(FX, exist_ok=True)
    L = []
    b = BIOMA
    # ---------- L1 BIOMA PRODUTO (pg10 do deck: painel verde a esquerda, fachada a direita)
    lw, lh_ = lg("bioma_logo", 300)
    L.append({"layout_id": "bioma_produto", "brand": "bioma", "canvas": {"width": 1920, "height": 1080, "background": b["bg"]},
              "elements": [
                  I("hero", "HERO", 0.8, "bioma_fachada", 760, 0, 1160, 1080, crop_for(man["bioma_fachada"], 1160, 1080, (0.62, 0.5))),
                  I("logo", "LOGO", 0.7, "bioma_logo", 110, 110, lw, lh_, [0, 0, 1, 1], z=6),
                  T("headline", "HEADLINE", 1.0, "Chegou o primeiro residencial da Cidade Center Norte", 110, 330, 580, 260, b["title"], 64, 600, b["cream"], lh=1.05),
                  T("selo", "PRODUCT_INFO", 0.6, "2 e 3 suítes · 93 a 150 m²", 110, 620, 560, 44, b["support"], 34, 600, b["light"]),
                  T("cta", "CTA", 0.65, "Agende sua visita · 11 99943.5903", 110, 700, 560, 40, b["support"], 28, 400, b["cream"]),
                  T("legal", "LEGAL", 0.3, LEGAL_BIOMA, 110, 860, 600, 170, b["text"], 13, 400, b["cream"], lh=1.3),
              ],
              "relations": [{"source": "logo", "target": "headline", "type": "BRANDS"},
                            {"source": "selo", "target": "headline", "type": "SUPPORTS"},
                            {"source": "cta", "target": "headline", "type": "CALLS_TO_ACTION"},
                            {"source": "legal", "target": "selo", "type": "EXPLAINS"}],
              "groups": [{"id": "g_marca", "members": ["logo", "headline"], "mode": "ADJACENT"},
                         {"id": "g_info", "members": ["selo", "cta"], "mode": "ADJACENT"}],
              "text_over_image": []})
    # ---------- L2 BIOMA SUSTENTABILIDADE (titulo + 3 icones com rotulo + legal longo)
    lw, lh_ = lg("bioma_logo", 240)
    els = [I("hero", "HERO", 0.5, "bioma_fachada", 0, 0, 1920, 420, crop_for(man["bioma_fachada"], 1920, 420, (0.6, 0.45))),
           I("logo", "LOGO", 0.6, "bioma_logo", 1580, 470, lw, lh_, [0, 0, 1, 1], z=6),
           T("headline", "HEADLINE", 1.0, "Viver bem também é cuidar do amanhã", 110, 470, 1300, 90, b["title"], 72, 600, b["cream"], lh=1.05)]
    labels = [("solar", "Previsão para aquecimento solar (2)"), ("chuva", "Reaproveitamento de água das chuvas (3)"), ("coleta", "Paisagismo com árvores nativas (4)")]
    for i, (k, t) in enumerate(labels):
        x = 110 + i * 560
        els.append(I("icon_" + k, "PRODUCT_ATTRIBUTE", 0.55, "bioma_icon_" + k, x, 620, 120, 120, [0, 0, 1, 1], z=4))
        els.append(T("lbl_" + k, "PRODUCT_ATTRIBUTE", 0.55, t, x + 140, 640, 380, 80, b["support"], 28, 600, b["cream"]))
    els.append(T("legal", "LEGAL", 0.3, LEGAL_BIOMA, 110, 860, 1700, 120, b["text"], 14, 400, b["cream"], lh=1.3))
    rel = [{"source": "logo", "target": "headline", "type": "BRANDS"}] + \
          [{"source": "lbl_" + k, "target": "icon_" + k, "type": "BELONGS_TO"} for k, _ in labels] + \
          [{"source": "legal", "target": "lbl_" + k, "type": "EXPLAINS"} for k, _ in labels]
    grp = [{"id": "g_" + k, "members": ["icon_" + k, "lbl_" + k], "mode": "ADJACENT"} for k, _ in labels]
    L.append({"layout_id": "bioma_sustentabilidade", "brand": "bioma", "canvas": {"width": 1920, "height": 1080, "background": b["bg"]},
              "elements": els, "relations": rel, "groups": grp, "text_over_image": []})
    # ---------- L3 BIOMA PISCINA (imagem sangrada, titulo sobre imagem com faixa multiply)
    lw, lh_ = lg("bioma_logo", 260)
    L.append({"layout_id": "bioma_piscina", "brand": "bioma", "canvas": {"width": 1920, "height": 1080, "background": b["bg"]},
              "elements": [
                  I("hero", "HERO", 0.9, "bioma_piscina", 0, 0, 1920, 1080, crop_for(man["bioma_piscina"], 1920, 1080, (0.5, 0.6))),
                  S("faixa", 0, 0, 900, 1080, "#1E3B2C", 0.82),
                  I("logo", "LOGO", 0.7, "bioma_logo", 110, 100, lw, lh_, [0, 0, 1, 1], z=6),
                  T("headline", "HEADLINE", 1.0, "Um novo norte para viver a vida ao ar livre", 110, 320, 680, 260, b["title"], 70, 600, b["cream"], lh=1.05),
                  T("cta", "CTA", 0.65, "Conheça o decorado · 11 99943.5903", 110, 640, 680, 40, b["support"], 30, 600, b["light"]),
                  T("legal", "LEGAL", 0.3, LEGAL_BIOMA, 110, 860, 700, 170, b["text"], 12, 400, b["cream"], lh=1.3),
              ],
              "relations": [{"source": "logo", "target": "headline", "type": "BRANDS"},
                            {"source": "cta", "target": "headline", "type": "CALLS_TO_ACTION"}],
              "groups": [{"id": "g_marca", "members": ["logo", "headline"], "mode": "ADJACENT"}],
              "text_over_image": ["headline", "cta", "legal", "logo"]})
    o = OTIUM
    # ---------- O1 OTIUM PRODUTO (fachada a esquerda, texto a direita)
    lw, lh_ = lg("otium_logo", 280)
    L.append({"layout_id": "otium_produto", "brand": "otium", "canvas": {"width": 1920, "height": 1080, "background": o["bg"]},
              "elements": [
                  I("hero", "HERO", 0.8, "otium_fachada", 0, 0, 1000, 1080, crop_for(man["otium_fachada"], 1000, 1080, (0.4, 0.5))),
                  I("logo", "LOGO", 0.7, "otium_logo", 1110, 120, lw, lh_, [0, 0, 1, 1], z=6),
                  T("headline", "HEADLINE", 1.0, "Jardim das Perdizes, no seu ritmo", 1110, 360, 700, 200, o["title"], 72, 700, o["cream"], lh=1.05),
                  T("selo", "PRODUCT_INFO", 0.6, "3 suítes · 142 m² · 2 vagas", 1110, 610, 700, 44, o["support"], 34, 600, o["light"]),
                  T("cta", "CTA", 0.65, "Visite o stand · otiumartefacto.com.br", 1110, 690, 700, 40, o["text"], 26, 400, o["cream"]),
              ],
              "relations": [{"source": "logo", "target": "headline", "type": "BRANDS"},
                            {"source": "selo", "target": "headline", "type": "SUPPORTS"},
                            {"source": "cta", "target": "headline", "type": "CALLS_TO_ACTION"}],
              "groups": [{"id": "g_info", "members": ["selo", "cta"], "mode": "ADJACENT"}],
              "text_over_image": []})
    # ---------- O2 OTIUM SPA (imagem sangrada, texto embaixo com faixa)
    lw, lh_ = lg("otium_logo", 240)
    L.append({"layout_id": "otium_spa", "brand": "otium", "canvas": {"width": 1920, "height": 1080, "background": o["bg"]},
              "elements": [
                  I("hero", "HERO", 0.9, "otium_spa", 0, 0, 1920, 1080, crop_for(man["otium_spa"], 1920, 1080, (0.5, 0.5))),
                  S("faixa", 0, 760, 1920, 320, "#2B2A2D", 0.85),
                  I("logo", "LOGO", 0.7, "otium_logo", 1560, 830, lw, lh_, [0, 0, 1, 1], z=6),
                  T("headline", "HEADLINE", 1.0, "Um spa para chamar de seu", 110, 800, 1300, 100, o["title"], 76, 700, o["cream"], lh=1.05),
                  T("cta", "CTA", 0.6, "Lazer completo no rooftop · Visite o decorado", 110, 940, 1300, 44, o["support"], 32, 400, o["light"]),
              ],
              "relations": [{"source": "logo", "target": "headline", "type": "BRANDS"},
                            {"source": "cta", "target": "headline", "type": "CALLS_TO_ACTION"}],
              "groups": [],
              "text_over_image": ["headline", "cta", "logo"]})
    # ---------- O3 OTIUM LIVING (imagem baixa resolucao, marca a meia altura)
    lw, lh_ = lg("otium_logo", 260)
    L.append({"layout_id": "otium_living", "brand": "otium", "canvas": {"width": 1920, "height": 1080, "background": o["bg"]},
              "elements": [
                  I("hero", "HERO", 0.8, "otium_living", 0, 0, 1920, 830, crop_for(man["otium_living"], 1920, 830, (0.5, 0.5))),
                  I("logo", "LOGO", 0.7, "otium_logo", 110, 880, lw, lh_, [0, 0, 1, 1], z=6),
                  T("headline", "HEADLINE", 1.0, "Living integrado com vista verde", 520, 870, 1000, 80, o["title"], 60, 700, o["cream"], lh=1.05),
                  T("selo", "PRODUCT_INFO", 0.55, "Planta de 142 m² com terraço gourmet", 520, 970, 1000, 44, o["support"], 30, 400, o["light"]),
              ],
              "relations": [{"source": "logo", "target": "headline", "type": "BRANDS"},
                            {"source": "selo", "target": "headline", "type": "SUPPORTS"}],
              "groups": [{"id": "g_txt", "members": ["headline", "selo"], "mode": "ADJACENT"}],
              "text_over_image": []})
    for l in L:
        l["schema_version"] = "bancada-0.1"
        json.dump(l, open(os.path.join(FX, l["layout_id"] + ".json"), "w"), indent=1, ensure_ascii=False)

    # ---------- Tabela de formatos (dado, nao codigo). Medidas-padrao de canal do caso Bioma.
    formats = {
        "email_600x1200": {"width": 600, "height": 1200, "margin": 32, "safe": [0, 0, 0, 0],
                            "min_font": {"HEADLINE": 26, "SUBHEADLINE": 18, "PRODUCT_INFO": 15, "PRODUCT_ATTRIBUTE": 14, "CTA": 15, "LEGAL": 9, "OTHER": 12},
                            "logo_min_width": {"bioma": 130, "otium": 110}},
        "post_1080x1350": {"width": 1080, "height": 1350, "margin": 60, "safe": [0, 0, 0, 0],
                            "min_font": {"HEADLINE": 44, "SUBHEADLINE": 30, "PRODUCT_INFO": 26, "PRODUCT_ATTRIBUTE": 24, "CTA": 26, "LEGAL": 14, "OTHER": 20},
                            "logo_min_width": {"bioma": 130, "otium": 110}},
        "card_1080x1080": {"width": 1080, "height": 1080, "margin": 60, "safe": [0, 0, 0, 0],
                            "min_font": {"HEADLINE": 44, "SUBHEADLINE": 30, "PRODUCT_INFO": 26, "PRODUCT_ATTRIBUTE": 24, "CTA": 26, "LEGAL": 14, "OTHER": 20},
                            "logo_min_width": {"bioma": 130, "otium": 110}},
        "stories_1080x1920": {"width": 1080, "height": 1920, "margin": 64, "safe": [250, 0, 340, 0],
                               "min_font": {"HEADLINE": 52, "SUBHEADLINE": 34, "PRODUCT_INFO": 30, "PRODUCT_ATTRIBUTE": 28, "CTA": 30, "LEGAL": 16, "OTHER": 22},
                               "logo_min_width": {"bioma": 130, "otium": 110}},
        "banner_970x250": {"width": 970, "height": 250, "margin": 16, "safe": [0, 0, 0, 0],
                            "min_font": {"HEADLINE": 24, "SUBHEADLINE": 16, "PRODUCT_INFO": 14, "PRODUCT_ATTRIBUTE": 13, "CTA": 14, "LEGAL": 8, "OTHER": 11},
                            "logo_min_width": {"bioma": 130, "otium": 110}},
    }
    # T1: regioes normalizadas [x,y,w,h] declaradas uma vez por formato (matriz desenhada por pessoa,
    # vale para qualquer KV; padrao de medidas da P31/P33)
    templates = {
        "email_600x1200": {"top": [0, 0.035, 1, 0.20], "hero": [0, 0.25, 1, 0.36], "mid": [0, 0.63, 1, 0.22], "legal": [0, 0.86, 1, 0.12], "align": "center"},
        "post_1080x1350": {"top": [0, 0.045, 1, 0.25], "hero": [0, 0.31, 1, 0.38], "mid": [0, 0.71, 1, 0.14], "legal": [0, 0.86, 1, 0.11], "align": "left"},
        "card_1080x1080": {"top": [0, 0.055, 1, 0.25], "hero": [0, 0.33, 1, 0.34], "mid": [0, 0.69, 1, 0.14], "legal": [0, 0.84, 1, 0.13], "align": "left"},
        "stories_1080x1920": {"top": [0, 0.14, 1, 0.16], "hero": [0, 0.31, 1, 0.29], "mid": [0, 0.61, 1, 0.08], "legal": [0, 0.70, 1, 0.085], "align": "center"},
        "banner_970x250": {"hero": [0, 0, 0.28, 1], "top": [0.30, 0.06, 0.48, 0.56], "mid": [0.30, 0.62, 0.48, 0.16], "legal": [0.30, 0.78, 0.48, 0.20], "logo": [0.80, 0.1, 0.18, 0.8], "align": "left"},
    }
    for k, v in templates.items():
        formats[k]["template"] = v
    json.dump(formats, open(os.path.join(FX, "formats.json"), "w"), indent=1)
    print("fixtures:", [l["layout_id"] for l in L])


if __name__ == "__main__":
    main()
