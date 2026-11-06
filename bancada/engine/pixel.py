"""Verificacoes no pixel (PNG exportado): contraste WCAG de cada texto contra o fundo real.

Uso: python3 pixel.py candidato.json medidas.json render.png peca_mestra.json  -> JSON em stdout
Contraste: 4,5:1 para texto normal, 3:1 para texto grande (>=32px, ou >=24px com peso >=600).
O fundo vem de uma segunda captura com o texto transparente; usa o pior decil dos pixels da caixa.
"""
import json, sys
import numpy as np
from PIL import Image


def lum(rgb):
    c = rgb / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=float)


def main():
    cand = json.load(open(sys.argv[1]))
    meas = json.load(open(sys.argv[2]))
    im = np.asarray(Image.open(sys.argv[3].replace(".png", ".bg.png")).convert("RGB")).astype(float)
    src = json.load(open(sys.argv[4]))
    srcroles = {e["id"]: e.get("role") for e in src["elements"]}
    H, W = im.shape[:2]
    hard, worst = [], 99.0
    for e in cand["elements"]:
        if e.get("type") != "TEXT" or e["id"] not in meas:
            continue
        m = meas[e["id"]]
        x0, y0 = max(0, int(m["x"])), max(0, int(m["y"]))
        x1, y1 = min(W, int(m["x"] + m["w"]) + 1), min(H, int(m["y"] + m["h"]) + 1)
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        patch = im[y0:y1, x0:x1].reshape(-1, 3)
        tc = hexrgb(e["style"]["color"])
        bg = patch  # captura sem texto: tudo na caixa e fundo
        lt = lum(tc[None, :])[0]
        lb = lum(bg)
        ratios = (np.maximum(lb, lt) + 0.05) / (np.minimum(lb, lt) + 0.05)
        r = float(np.percentile(ratios, 10))
        size, weight = float(e["style"]["size"]), int(e["style"].get("weight", 400))
        large = size >= 32 or (size >= 24 and weight >= 600)
        need = 3.0 if large else 4.5
        worst = min(worst, r / need)
        if r < need:
            hard.append({"check": "contraste", "id": e["id"], "status": "FAIL",
                         "detail": f"contraste {r:.2f}:1 < {need}:1 ({srcroles.get(e['id'])})"})
    print(json.dumps({"fails": len(hard), "hard": hard, "soft": {"contraste_folga": round(min(worst, 3.0), 3)}}))


if __name__ == "__main__":
    main()
