import json, copy, sys
src = json.load(open('fixtures/otium_living.json'))
E = {e['id']: e for e in src['elements']}
def hero_crop(W, H, cx=0.39):
    # full asset height, centred on protected area centre x=0.39
    w = (W / H) * 520 / 1200
    x0 = min(max(cx - w / 2, 0), 1 - w, 0.2)
    return [round(x0, 5), 0, round(w, 5), 1]
def build(fmt, W, H, g):
    out = {"schema_version": "bancada-0.1", "layout_id": "otium_living", "brand": "otium", "_format": fmt,
           "canvas": {"width": W, "height": H, "background": "#2B2A2D"}, "elements": []}
    for id_ in ['hero', 'logo', 'headline', 'selo']:
        e = copy.deepcopy(E[id_]); x, y, w, h = g[id_][:4]
        e['geometry'] = {"x": x, "y": y, "width": w, "height": h, "z": e['geometry']['z']}
        if id_ == 'hero': e['crop'] = hero_crop(w, h, g.get('cx', 0.39))
        if e['type'] == 'TEXT':
            e['style']['size'] = g[id_][4]; e['style']['line_height'] = g[id_][5]; e['style']['align'] = g[id_][6]
        out['elements'].append(e)
    out['relations'] = src['relations']; out['groups'] = src['groups']; out['text_over_image'] = []
    json.dump(out, open(f'runs/R01/candidates/R3/otium_living__{fmt}.json', 'w'), indent=1, ensure_ascii=False)
F = {
 'email_600x1200': (600, 1200, {'hero': (0, 0, 600, 640), 'logo': (48, 777, 170, 77),
    'headline': (48, 898, 440, 112, 52, 1.05, 'left'), 'selo': (48, 1030, 504, 36, 26, 1.15, 'left')}),
 'post_1080x1350': (1080, 1350, {'hero': (0, 0, 1080, 780), 'logo': (80, 886, 200, 90),
    'headline': (80, 1020, 720, 162, 76, 1.05, 'left'), 'selo': (80, 1204, 720, 48, 34, 1.15, 'left'), 'cx': 0.44}),
 'card_1080x1080': (1080, 1080, {'hero': (0, 0, 1080, 680), 'logo': (80, 830, 220, 99),
    'headline': (380, 785, 560, 136, 64, 1.05, 'left'), 'selo': (380, 939, 640, 42, 30, 1.15, 'left')}),
 'stories_1080x1920': (1080, 1920, {'hero': (0, 0, 1080, 1000), 'logo': (80, 1091, 240, 108),
    'headline': (80, 1247, 700, 170, 80, 1.05, 'left'), 'selo': (80, 1443, 920, 52, 38, 1.15, 'left'), 'cx': 0.41}),
 'banner_970x250': (970, 250, {'hero': (0, 0, 330, 250), 'logo': (360, 97, 124, 56),
    'headline': (512, 65, 340, 82, 38, 1.05, 'left'), 'selo': (512, 159, 430, 30, 22, 1.15, 'left')}),
}
for k in (sys.argv[1:] or F):
    W, H, g = F[k]; build(k, W, H, g)
