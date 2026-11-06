// Bancada de desdobramento — biblioteca que roda DENTRO do Chromium.
// Renderiza Layout IR, mede texto de verdade (DOM), roda as verificacoes geometricas
// e implementa os motores deterministicos (letterbox, resize, reflow cego e semantico).
// O mesmo codigo de medicao serve ao gerador e ao verificador (achado C-07 da auditoria).
(function () {
  const B = (window.B = {});
  B.assets = {};
  B.formats = {};
  B.assetBase = "";

  const clone = (o) => JSON.parse(JSON.stringify(o));
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const area = (r) => Math.max(0, r.w) * Math.max(0, r.h);
  const inter = (a, b) => {
    const x = Math.max(a.x, b.x), y = Math.max(a.y, b.y);
    const X = Math.min(a.x + a.w, b.x + b.w), Y = Math.min(a.y + a.h, b.y + b.h);
    return X > x && Y > y ? { x, y, w: X - x, h: Y - y } : null;
  };
  const box = (e) => ({ x: e.geometry.x, y: e.geometry.y, w: e.geometry.width, h: e.geometry.height });
  const CONTENT = (e) => e.type !== "SHAPE";

  // ---------------------------------------------------------------- render
  B.render = function (ir, host) {
    host = host || document.getElementById("stage");
    host.innerHTML = "";
    const root = document.createElement("div");
    root.id = "root";
    Object.assign(root.style, { position: "relative", width: ir.canvas.width + "px", height: ir.canvas.height + "px",
      background: ir.canvas.background || "#fff", overflow: "hidden" });
    const els = [...ir.elements].sort((a, b) => (a.geometry.z || 0) - (b.geometry.z || 0));
    for (const e of els) {
      const g = e.geometry;
      const d = document.createElement("div");
      d.dataset.id = e.id;
      Object.assign(d.style, { position: "absolute", left: g.x + "px", top: g.y + "px", width: g.width + "px", height: g.height + "px" });
      if (e.type === "TEXT") {
        const s = e.style;
        Object.assign(d.style, { fontFamily: `'${s.font}'`, fontSize: s.size + "px", fontWeight: s.weight, lineHeight: (s.line_height || 1.15),
          color: s.color, textAlign: s.align || "left", whiteSpace: "normal", overflowWrap: "normal", overflow: "visible" });
        d.textContent = e.text;
      } else if (e.type === "IMAGE") {
        const a = B.assets[e.asset];
        const c = e.crop || [0, 0, 1, 1];
        d.style.overflow = "hidden";
        const im = document.createElement("img");
        im.src = B.assetBase + a.file;
        const dw = g.width / c[2], dh = g.height / c[3];
        Object.assign(im.style, { position: "absolute", left: -c[0] * dw + "px", top: -c[1] * dh + "px", width: dw + "px", height: dh + "px", maxWidth: "none" });
        d.appendChild(im);
      } else if (e.type === "SHAPE") {
        Object.assign(d.style, { background: e.style.color, opacity: e.style.opacity == null ? 1 : e.style.opacity });
      }
      root.appendChild(d);
    }
    host.appendChild(root);
    return root;
  };

  B.ready = async function () {
    await document.fonts.ready;
    const imgs = [...document.images];
    await Promise.all(imgs.map((i) => (i.complete ? 0 : new Promise((r) => { i.onload = i.onerror = r; }))));
  };

  // extensao real do texto (uniao dos retangulos de linha), relativa ao canvas
  B.measure = function (ir) {
    const root = document.getElementById("root");
    const R = root.getBoundingClientRect();
    const out = {};
    for (const e of ir.elements) {
      if (e.type !== "TEXT") continue;
      const d = root.querySelector(`[data-id="${CSS.escape(e.id)}"]`);
      const rg = document.createRange();
      rg.selectNodeContents(d);
      const rects = [...rg.getClientRects()].filter((r) => r.width > 0);
      if (!rects.length) { out[e.id] = { x: e.geometry.x, y: e.geometry.y, w: 0, h: 0, lines: 0 }; continue; }
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      const tops = new Set();
      for (const r of rects) { x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); tops.add(Math.round(r.top)); }
      out[e.id] = { x: x0 - R.left, y: y0 - R.top, w: x1 - x0, h: y1 - y0, lines: tops.size };
    }
    return out;
  };

  // mede um bloco de texto numa largura (primitiva compartilhada pelo gerador)
  let probe;
  B.textHeight = function (text, style, width) {
    if (!probe) { probe = document.createElement("div"); probe.style.cssText = "position:absolute;left:-99999px;top:0;visibility:hidden"; document.body.appendChild(probe); }
    Object.assign(probe.style, { width: width + "px", fontFamily: `'${style.font}'`, fontSize: style.size + "px", fontWeight: style.weight,
      lineHeight: style.line_height || 1.15, whiteSpace: "normal" });
    probe.textContent = text;
    const rg = document.createRange(); rg.selectNodeContents(probe);
    const rects = [...rg.getClientRects()].filter((r) => r.width > 0);
    let maxw = 0; for (const r of rects) maxw = Math.max(maxw, r.width);
    const lh = style.size * (style.line_height || 1.15);
    const tops = new Set(rects.map((r) => Math.round(r.top)));
    // altura = extensao real dos glifos (a mesma que o verificador mede), nunca menor que as linhas
    const P0 = probe.getBoundingClientRect().top;
    let bot = 0; for (const r of rects) bot = Math.max(bot, r.bottom - P0);
    return { h: Math.ceil(Math.max(tops.size * lh, bot) + 1), w: Math.ceil(maxw), lines: tops.size };
  };

  // ---------------------------------------------------------------- checks
  // src = peca-mestra (com semantica completa: o avaliador sempre usa a fonte da verdade)
  B.checks = function (src, cand, fmtKey, meas) {
    const F = B.formats[fmtKey];
    const W = cand.canvas.width, H = cand.canvas.height;
    const hard = [];
    const add = (check, id, ok, detail, sev = "FAIL") => { if (!ok) hard.push({ check, id, status: sev, detail }); };
    const byId = Object.fromEntries(cand.elements.map((e) => [e.id, e]));
    const srcBy = Object.fromEntries(src.elements.map((e) => [e.id, e]));
    add("canvas", "-", W === F.width && H === F.height, `canvas ${W}x${H} != ${F.width}x${F.height}`);
    // H1 conteudo completo e intocado (permissoes: rewrite/remove/replace proibidos)
    for (const s of src.elements) {
      if (!CONTENT(s)) continue;
      const c = byId[s.id];
      add("conteudo_presente", s.id, !!c, "elemento removido");
      if (!c) continue;
      if (s.type === "TEXT") add("texto_identico", s.id, c.text === s.text, "texto alterado");
      if (s.type === "IMAGE") add("ativo_identico", s.id, c.asset === s.asset, "ativo trocado");
      add("tipo_identico", s.id, c.type === s.type, "tipo alterado");
    }
    for (const c of cand.elements) if (CONTENT(c) && !srcBy[c.id]) add("conteudo_inventado", c.id, false, "elemento de conteudo que nao existe na peca-mestra");
    const safe = { x: F.margin + F.safe[3], y: F.margin + F.safe[0], w: W - 2 * F.margin - F.safe[1] - F.safe[3], h: H - 2 * F.margin - F.safe[0] - F.safe[2] };
    const textExt = {};
    for (const c of cand.elements) {
      const s = srcBy[c.id]; if (!s) continue;
      const b = box(c);
      const role = s.role;
      // H2 dentro do canvas (imagem pode sangrar exatamente ate a borda)
      add("dentro_do_canvas", c.id, b.x >= -0.5 && b.y >= -0.5 && b.x + b.w <= W + 0.5 && b.y + b.h <= H + 0.5, `caixa ${JSON.stringify(b)} sai do canvas`);
      if (c.type === "TEXT") {
        const m = meas[c.id] || { x: b.x, y: b.y, w: 0, h: 0 };
        textExt[c.id] = m;
        add("texto_sem_estouro", c.id, m.y + m.h <= b.y + b.h + 1.5 && m.x + m.w <= b.x + b.w + 1.5 && m.x >= b.x - 1.5, `texto mede ${Math.round(m.h)}px de altura numa caixa de ${Math.round(b.h)}px`);
        const mf = F.min_font[role] || F.min_font.OTHER;
        add("corpo_minimo", c.id, c.style.size >= mf - 0.01, `corpo ${c.style.size}px < minimo ${mf}px para ${role}`);
        const ext = { x: Math.min(m.x, b.x), y: Math.min(m.y, b.y), w: Math.max(m.w, 1), h: Math.max(m.h, 1) };
        const ex = { x: m.x, y: m.y, w: m.w, h: m.h };
        add("area_segura", c.id, ex.x >= safe.x - 1 && ex.y >= safe.y - 1 && ex.x + ex.w <= safe.x + safe.w + 1 && ex.y + ex.h <= safe.y + safe.h + 1, "texto fora da area segura/margem");
        add("fonte_da_marca", c.id, c.style.font === s.style.font && String(c.style.weight) === String(s.style.weight) && c.style.color.toLowerCase() === s.style.color.toLowerCase(), "fonte, peso ou cor trocados");
        add("texto_cresceu_demais", c.id, true, "");
      }
      if (c.type === "IMAGE") {
        const a = B.assets[c.asset];
        const cr = c.crop || [0, 0, 1, 1];
        const okWin = cr[0] >= -0.001 && cr[1] >= -0.001 && cr[0] + cr[2] <= 1.001 && cr[1] + cr[3] <= 1.001 && cr[2] > 0 && cr[3] > 0;
        add("janela_de_recorte_valida", c.id, okWin, `janela ${JSON.stringify(cr)}`);
        const arWin = (cr[2] * a.width) / (cr[3] * a.height), arBox = b.w / b.h;
        add("imagem_sem_distorcao", c.id, Math.abs(arWin / arBox - 1) <= 0.015, `aspecto janela ${arWin.toFixed(3)} x caixa ${arBox.toFixed(3)}`);
        if (role === "LOGO") {
          add("logo_inteiro", c.id, cr[0] <= 0.001 && cr[1] <= 0.001 && cr[2] >= 0.999 && cr[3] >= 0.999, "logo recortado");
          const lm = (F.logo_min_width || {})[src.brand] || 100;
          add("logo_tamanho_minimo", c.id, b.w >= lm - 0.5, `logo ${Math.round(b.w)}px < ${lm}px`);
          add("logo_na_area_segura", c.id, b.x >= safe.x - 1 && b.y >= safe.y - 1 && b.x + b.w <= safe.x + safe.w + 1 && b.y + b.h <= safe.y + safe.h + 1, "logo fora da area segura");
        }
        if (a.real_size) {
          const up = (b.w / cr[2]) / a.real_size[0];
          if (up > 1.5) hard.push({ check: "resolucao", id: c.id, status: "WARN", detail: `ampliacao ${up.toFixed(2)}x do original` });
        }
      }
    }
    // colisoes: texto x texto, texto x logo, texto x icones; logo ocluido
    const texts = cand.elements.filter((e) => e.type === "TEXT");
    for (let i = 0; i < texts.length; i++) for (let j = i + 1; j < texts.length; j++) {
      const a = textExt[texts[i].id], b = textExt[texts[j].id];
      if (a && b && inter(a, b) && area(inter(a, b)) > 4) add("texto_sobre_texto", texts[i].id + "/" + texts[j].id, false, "textos se sobrepoem");
    }
    const zOf = (e) => e.geometry.z || 0;
    for (const im of cand.elements.filter((e) => e.type === "IMAGE")) {
      const s = srcBy[im.id]; if (!s) continue;
      const ib = box(im);
      for (const t of texts) {
        const te = textExt[t.id]; if (!te) continue;
        const it = inter(te, ib); if (!it || area(it) < 4) continue;
        if (s.role === "LOGO" || s.role === "PRODUCT_ATTRIBUTE") { add("texto_sobre_logo_ou_icone", t.id + "/" + im.id, false, "texto encosta no logo/icone"); continue; }
        // texto sobre foto: permitido se a peca-mestra ja faz, ou se ha faixa (SHAPE) cobrindo o texto
        const allowed = (src.text_over_image || []).includes(t.id);
        const scrim = cand.elements.some((sh) => sh.type === "SHAPE" && (sh.style.opacity ?? 1) >= 0.7 && zOf(sh) > zOf(im) && zOf(sh) < zOf(t) && inter(box(sh), te) && area(inter(box(sh), te)) >= 0.95 * area(te));
        add("texto_sobre_foto_sem_faixa", t.id, allowed || scrim, "texto sobre a foto sem faixa de legibilidade");
      }
    }
    for (const lg of cand.elements.filter((e) => srcBy[e.id] && srcBy[e.id].role === "LOGO")) {
      for (const o of cand.elements) {
        if (o === lg || zOf(o) <= zOf(lg)) continue;
        const ob = o.type === "TEXT" ? textExt[o.id] : box(o);
        const it = ob && inter(ob, box(lg));
        if (it && area(it) > 0.02 * area(box(lg))) add("logo_ocluido", lg.id, false, `coberto por ${o.id}`);
      }
    }
    // elementos de conteudo nao-texto sobrepostos entre si (exceto foto de fundo)
    const imgs = cand.elements.filter((e) => e.type === "IMAGE" && srcBy[e.id] && srcBy[e.id].role !== "HERO");
    for (let i = 0; i < imgs.length; i++) for (let j = i + 1; j < imgs.length; j++) {
      const it = inter(box(imgs[i]), box(imgs[j]));
      if (it && area(it) > 4) add("imagens_sobrepostas", imgs[i].id + "/" + imgs[j].id, false, "imagens se sobrepoem");
    }
    // area protegida da foto principal visivel (predio/piscina nao some)
    const visFrac = (ir, m) => {
      const h = ir.elements.find((e) => (srcBy[e.id] || {}).role === "HERO");
      if (!h) return 1;
      const a = B.assets[h.asset], p = a.protected, cr = h.crop || [0, 0, 1, 1], b = box(h);
      const pb = { x: b.x + ((p[0] - cr[0]) / cr[2]) * b.w, y: b.y + ((p[1] - cr[1]) / cr[3]) * b.h, w: (p[2] / cr[2]) * b.w, h: (p[3] / cr[3]) * b.h };
      const total = area(pb); if (total <= 0) return 0;
      const vis = inter(pb, b) && inter(inter(pb, b), { x: 0, y: 0, w: ir.canvas.width, h: ir.canvas.height });
      if (!vis) return 0;
      // amostragem: tira o que esta coberto por elementos acima
      let n = 0, ok = 0;
      for (let i = 0; i < 24; i++) for (let j = 0; j < 24; j++) {
        const x = pb.x + (i + 0.5) / 24 * pb.w, y = pb.y + (j + 0.5) / 24 * pb.h; n++;
        if (x < vis.x || x > vis.x + vis.w || y < vis.y || y > vis.y + vis.h) continue;
        let cov = false;
        for (const o of ir.elements) {
          if (o === h || (o.geometry.z || 0) <= (h.geometry.z || 0)) continue;
          if (o.type === "SHAPE" && (o.style.opacity ?? 1) < 0.7) continue;
          const ob = o.type === "TEXT" ? (m[o.id] || box(o)) : box(o);
          if (x >= ob.x && x <= ob.x + ob.w && y >= ob.y && y <= ob.y + ob.h) { cov = true; break; }
        }
        if (!cov) ok++;
      }
      return ok / n;
    };
    const vSrc = B._srcVis != null ? B._srcVis : 1;
    const vC = visFrac(cand, meas);
    const need = Math.min(0.8, vSrc * 0.9);
    add("area_protegida_visivel", "hero", vC >= need, `so ${(vC * 100).toFixed(0)}% do predio/piscina visivel (minimo ${(need * 100).toFixed(0)}%)`);

    // ------------------------------------------------------------ metricas suaves (0..1)
    const soft = {};
    const content = cand.elements.filter((e) => srcBy[e.id] && CONTENT(e));
    // preenchimento: fracao do canvas ocupada por algum elemento
    let cov = 0; const N = 40;
    for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
      const x = (i + 0.5) / N * W, y = (j + 0.5) / N * H;
      if (cand.elements.some((e) => { const b = e.type === "TEXT" ? (textExt[e.id] || box(e)) : box(e); return x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h; })) cov++;
    }
    soft.preenchimento = Math.min(1, cov / (N * N) / 0.8);
    // quase-alinhado (artigo 01): bordas esquerdas/centros que quase coincidem
    const edges = content.filter((e) => e.type === "TEXT" || (srcBy[e.id].role === "LOGO")).map((e) => {
      const b = e.type === "TEXT" ? textExt[e.id] : box(e); return [b.x, b.x + b.w / 2, b.x + b.w];
    });
    let near = 0;
    for (let i = 0; i < edges.length; i++) for (let j = i + 1; j < edges.length; j++) for (let k = 0; k < 3; k++) {
      const d = Math.abs(edges[i][k] - edges[j][k]); if (d > 2 && d < 0.02 * W) near++;
    }
    soft.alinhamento = 1 - Math.min(1, near / 4);
    // fidelidade: relacoes de tamanho (Size Rel) e ordem de leitura e hierarquia tipografica
    const ids = content.map((e) => e.id);
    const areaOf = (ir, id, m) => { const e = ir.elements.find((x) => x.id === id); if (!e) return 0; if (e.type === "TEXT") { const t = m ? m[id] : null; return t ? t.w * t.h : area(box(e)); } return area(box(e)); };
    const sm = B._srcMeas || {};
    let sr = 0, st = 0;
    const rel = (a, b) => (a > b * 1.2 ? 1 : a < b / 1.2 ? -1 : 0);
    for (let i = 0; i < ids.length; i++) for (let j = i + 1; j < ids.length; j++) {
      st++;
      const s0 = rel(areaOf(src, ids[i], sm) / (src.canvas.width * src.canvas.height), areaOf(src, ids[j], sm) / (src.canvas.width * src.canvas.height));
      const c0 = rel(areaOf(cand, ids[i], textExt), areaOf(cand, ids[j], textExt));
      if (s0 === c0) sr++;
    }
    soft.size_rel = st ? sr / st : 1;
    const tau = (a, b) => { // kendall entre duas listas de valores pareados
      let c = 0, d = 0;
      for (let i = 0; i < a.length; i++) for (let j = i + 1; j < a.length; j++) { const s = Math.sign(a[i] - a[j]) * Math.sign(b[i] - b[j]); if (s > 0) c++; else if (s < 0) d++; }
      return c + d ? (c - d) / (c + d) : 1;
    };
    const tx = texts.filter((t) => srcBy[t.id]);
    soft.hierarquia = (tau(tx.map((t) => srcBy[t.id].style.size), tx.map((t) => t.style.size)) + 1) / 2;
    const top = content.filter((e) => srcBy[e.id].priority >= 0.6 && srcBy[e.id].role !== "HERO");
    const ord = (ir, e) => { const b = box(ir.elements.find((x) => x.id === e.id)); return (b.y + b.h / 2) / ir.canvas.height * 10 + (b.x + b.w / 2) / ir.canvas.width; };
    soft.ordem_leitura = (tau(top.map((e) => ord(src, e)), top.map((e) => ord(cand, e))) + 1) / 2;
    // escala tipografica: quanto o texto encolheu em relacao ao ideal do formato
    const k = Math.sqrt((W * H) / (src.canvas.width * src.canvas.height));
    soft.escala_texto = tx.length ? tx.reduce((s, t) => s + Math.min(1, t.style.size / Math.max(F.min_font[srcBy[t.id].role] || 10, srcBy[t.id].style.size * k)), 0) / tx.length : 1;
    // grupos que nao se separam (relacao preservada)
    let gk = 0, gt = 0;
    for (const g of src.groups || []) {
      const bs = g.members.map((id) => byId[id]).filter(Boolean).map((e) => (e.type === "TEXT" ? textExt[e.id] : box(e)));
      if (bs.length < 2) continue; gt++;
      let far = false;
      for (let i = 0; i < bs.length - 1; i++) {
        const a = bs[i], b = bs[i + 1];
        const dx = Math.max(0, Math.max(a.x, b.x) - Math.min(a.x + a.w, b.x + b.w)), dy = Math.max(0, Math.max(a.y, b.y) - Math.min(a.y + a.h, b.y + b.h));
        if (Math.hypot(dx, dy) > 0.12 * Math.min(W, H)) far = true;
      }
      if (!far) gk++;
    }
    soft.grupos = gt ? gk / gt : 1;
    const w = { preenchimento: 1.2, alinhamento: 0.8, size_rel: 1, hierarquia: 1, ordem_leitura: 1, escala_texto: 1, grupos: 1 };
    let sw = 0, ss = 0; for (const key in w) { ss += w[key] * soft[key]; sw += w[key]; }
    const fails = hard.filter((h) => h.status === "FAIL");
    return { eligible: fails.length === 0, fails: fails.length, warns: hard.length - fails.length, hard, soft, soft_score: ss / sw, protected_visible: vC };
  };

  // ---------------------------------------------------------------- motores
  // crop "cover" para uma caixa, colocando o foco (normalizado no ativo) no ponto alvo da caixa
  B.cover = function (assetId, bw, bh, focus, target, zoom) {
    const a = B.assets[assetId];
    focus = focus || [0.5, 0.5]; target = target || [0.5, 0.5]; zoom = zoom || 1;
    const arB = bw / bh, arI = a.width / a.height;
    let cw, ch;
    if (arI > arB) { ch = 1; cw = arB / arI; } else { cw = 1; ch = arI / arB; }
    cw /= zoom; ch /= zoom;
    const cx = clamp(focus[0] - target[0] * cw, 0, 1 - cw), cy = clamp(focus[1] - target[1] * ch, 0, 1 - ch);
    return [cx, cy, cw, ch].map((v) => Math.round(v * 10000) / 10000);
  };
  const protCenter = (assetId) => { const p = B.assets[assetId].protected; return [p[0] + p[2] / 2, p[1] + p[3] / 2]; };

  // visao "cega": sem papel, sem prioridade, sem relacoes, sem area protegida (achado C-01/G)
  B.blindView = function (src) {
    const v = clone(src);
    v.elements.forEach((e) => { e.role = e.type === "SHAPE" ? "DECOR" : "OTHER"; e.priority = 0.5; });
    v.relations = []; v.groups = []; v.text_over_image = [];
    v._blind = true;
    return v;
  };

  function ctx(view, fmtKey) {
    const F = B.formats[fmtKey];
    const W = F.width, H = F.height;
    const safe = { x: F.margin + F.safe[3], y: F.margin + F.safe[0], w: W - 2 * F.margin - F.safe[1] - F.safe[3], h: H - 2 * F.margin - F.safe[0] - F.safe[2] };
    const k = Math.sqrt((W * H) / (view.canvas.width * view.canvas.height));
    const blind = !!view._blind;
    const minFont = (e) => (blind ? Math.max(...Object.values(F.min_font).filter((x) => x <= F.min_font.OTHER)) : F.min_font[e.role] || F.min_font.OTHER);
    const logoMin = (F.logo_min_width || {})[view.brand] || 100;
    const isHero = (e) => (blind ? e === largestImage(view) : e.role === "HERO");
    const isLogo = (e) => !blind && e.role === "LOGO";
    return { F, W, H, safe, k, blind, minFont, logoMin, isHero, isLogo };
  }
  function largestImage(view) {
    let best = null; for (const e of view.elements) if (e.type === "IMAGE" && (!best || area(box(e)) > area(box(best)))) best = e; return best;
  }
  // ordem de colocacao: semantica = prioridade com grupos juntos; cega = ordem do documento (leitura)
  function flowOrder(view, C) {
    const items = view.elements.filter((e) => e.type !== "SHAPE" && !C.isHero(e));
    if (C.blind) return items.sort((a, b) => (a.geometry.y - b.geometry.y) || (a.geometry.x - b.geometry.x)).map((e) => [e]);
    const groupOf = {}; for (const g of view.groups || []) for (const m of g.members) groupOf[m] = g;
    const used = new Set(), out = [];
    const sorted = [...items].sort((a, b) => b.priority - a.priority);
    for (const e of sorted) {
      if (used.has(e.id)) continue;
      const g = groupOf[e.id];
      const mem = g ? g.members.map((id) => items.find((x) => x.id === id)).filter(Boolean) : [e];
      mem.sort((a, b) => (a.geometry.y - b.geometry.y) || (a.geometry.x - b.geometry.x));
      mem.forEach((m) => used.add(m.id));
      out.push(mem);
    }
    // LEGAL sempre por ultimo (convencao), HEADLINE-grupo primeiro
    out.sort((a, b) => (a.some((x) => x.role === "LEGAL") ? 1 : 0) - (b.some((x) => x.role === "LEGAL") ? 1 : 0));
    return out;
  }
  // um "bloco" e um grupo; se no original os membros estao lado a lado, vira linha
  function isRow(mem) {
    if (mem.length < 2) return false;
    const [a, b] = mem.map(box);
    const vo = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
    return vo > 0.3 * Math.min(a.h, b.h);
  }
  function sizeText(e, C, width, scale) {
    const st = Object.assign({}, e.style);
    st.size = Math.max(C.minFont(e), Math.round(e.style.size * C.k * scale));
    const m = B.textHeight(e.text, st, width);
    return { st, h: m.h, w: m.w };
  }
  function placeImageFit(e, C, maxW, maxH, scale) {
    const a = B.assets[e.asset];
    const ar = a.width / a.height;
    let w = e.geometry.width * C.k * scale;
    if (C.isLogo(e)) w = Math.max(w, C.logoMin);
    w = Math.min(w, maxW); let h = w / ar;
    if (h > maxH) { h = maxH; w = h * ar; }
    return { w, h };
  }
  // empilha blocos dentro de uma regiao; devolve elementos posicionados e altura usada
  function stack(blocks, C, region, P) {
    const placed = []; let y = region.y; const gap = Math.round(C.H * 0.022 * P.gap);
    const align = P.align;
    for (const mem of blocks) {
      if (isRow(mem)) {
        // linha: imagem pequena + texto (icone + rotulo), ou logo + texto
        const img = mem.find((m) => m.type === "IMAGE"), txt = mem.filter((m) => m.type === "TEXT");
        let x = region.x, rowH = 0; const row = [];
        if (img) {
          const s = placeImageFit(img, C, region.w * 0.3, region.h, P.tscale);
          row.push(Object.assign(clone(img), { geometry: { x, y, width: s.w, height: s.h, z: img.geometry.z }, crop: [0, 0, 1, 1] }));
          x += s.w + gap; rowH = Math.max(rowH, s.h);
        }
        for (const t of txt) {
          const tw = region.x + region.w - x;
          const s = sizeText(t, C, tw, P.tscale);
          row.push(Object.assign(clone(t), { style: s.st, geometry: { x, y, width: tw, height: s.h, z: t.geometry.z } }));
          rowH = Math.max(rowH, s.h);
        }
        // centraliza verticalmente na linha
        for (const r of row) r.geometry.y = y + (rowH - r.geometry.height) / 2;
        placed.push(...row); y += rowH + gap; continue;
      }
      for (const e of mem) {
        if (e.type === "TEXT") {
          const s = sizeText(e, C, region.w, P.tscale);
          s.st.align = align;
          placed.push(Object.assign(clone(e), { style: s.st, geometry: { x: region.x, y, width: region.w, height: s.h, z: e.geometry.z } }));
          y += s.h + gap;
        } else {
          const s = placeImageFit(e, C, region.w, region.h * 0.3, P.tscale);
          const x = align === "center" ? region.x + (region.w - s.w) / 2 : region.x;
          placed.push(Object.assign(clone(e), { geometry: { x, y, width: s.w, height: s.h, z: e.geometry.z }, crop: [0, 0, 1, 1] }));
          y += s.h + gap;
        }
      }
    }
    return { placed, used: y - region.y - gap };
  }
  // ajusta a escala tipografica ate o bloco caber na altura disponivel
  function fitStack(blocks, C, region, P, maxH) {
    let p = Object.assign({}, P), r;
    for (let i = 0; i < 14; i++) { r = stack(blocks, C, region, p); if (r.used <= maxH) break; p.tscale *= 0.9; p.gap *= 0.9; }
    return r;
  }
  const DEF = { heroFrac: 0.45, gap: 1, tscale: 1, align: "left", side: "auto", zoom: 1, legalBottom: true };

  // S1 — fluxo por prioridade em bandas ao longo do eixo dominante
  B.S1 = function (view, fmtKey, P) {
    P = Object.assign({}, DEF, P);
    const C = ctx(view, fmtKey); const out = baseCand(view, C);
    const hero = view.elements.find(C.isHero);
    const blocks = flowOrder(view, C);
    const wide = C.W / C.H > 2.2;
    if (wide) return wideLayout(view, C, P, hero, blocks, out);
    // divide blocos: os de cima (antes da foto) = grupo de maior prioridade; resto abaixo
    const legal = blocks.filter((b) => b.some((x) => x.role === "LEGAL"));
    const rest = blocks.filter((b) => !legal.includes(b));
    const topB = rest.slice(0, 1), botB = rest.slice(1).concat(legal);
    let heroH = hero ? Math.round(C.H * P.heroFrac) : 0;
    let t, b;
    for (let it = 0; it < 6; it++) {
      const avail = C.safe.h - heroH;
      t = fitStack(topB, C, { x: C.safe.x, y: C.safe.y, w: C.safe.w, h: avail }, P, avail * 0.4);
      b = fitStack(botB, C, { x: C.safe.x, y: 0, w: C.safe.w, h: avail }, P, avail - t.used - 2 * C.H * 0.02 * P.gap);
      if (t.used + b.used + heroH + 2 * C.H * 0.03 <= C.safe.h || !hero) break;
      heroH = Math.round(heroH * 0.85);
    }
    const gap = Math.round(C.H * 0.03 * P.gap);
    let y = C.safe.y;
    t.placed.forEach((e) => { e.geometry.y += 0; }); y += t.used + gap;
    out.elements.push(...t.placed);
    if (hero) {
      const hy = y; const hh = Math.max(40, heroH);
      const focus = C.blind ? [0.5, 0.5] : protCenter(hero.asset);
      out.elements.push(Object.assign(clone(hero), { geometry: { x: 0, y: hy, width: C.W, height: hh, z: 1 }, crop: B.cover(hero.asset, C.W, hh, focus, [0.5, 0.5], P.zoom) }));
      y = hy + hh + gap;
    }
    // bloco de baixo ancorado no fim da area segura
    const by = Math.max(y, C.safe.y + C.safe.h - b.used);
    b.placed.forEach((e) => { e.geometry.y += by; });
    out.elements.push(...b.placed);
    return out;
  };

  function wideLayout(view, C, P, hero, blocks, out) {
    // banner: foto numa coluna, logo na ponta, textos empilhados no meio, legal embaixo
    const logoB = blocks.filter((b) => b.length === 1 && b[0].type === "IMAGE" && (C.isLogo(b[0]) || C.blind));
    const legal = blocks.filter((b) => b.some((x) => x.role === "LEGAL"));
    let mid = blocks.filter((b) => !logoB.includes(b) && !legal.includes(b));
    const heroW = hero ? Math.round(C.W * 0.3 * (P.heroFrac / 0.45)) : 0;
    let x = 0;
    const heroLeft = P.side !== "right";
    if (hero) {
      const focus = C.blind ? [0.5, 0.5] : protCenter(hero.asset);
      out.elements.push(Object.assign(clone(hero), { geometry: { x: heroLeft ? 0 : C.W - heroW, y: 0, width: heroW, height: C.H, z: 1 }, crop: B.cover(hero.asset, heroW, C.H, focus, [0.5, 0.5], P.zoom) }));
    }
    const x0 = heroLeft ? Math.max(C.safe.x, heroW + C.F.margin) : C.safe.x;
    const x1 = heroLeft ? C.safe.x + C.safe.w : C.W - heroW - C.F.margin;
    let right = x1;
    for (const lb of logoB) {
      const s = placeImageFit(lb[0], C, (x1 - x0) * 0.22, C.safe.h * 0.8, P.tscale);
      right -= s.w;
      out.elements.push(Object.assign(clone(lb[0]), { geometry: { x: right, y: C.safe.y + (C.safe.h - s.h) / 2, width: s.w, height: s.h, z: 6 }, crop: [0, 0, 1, 1] }));
      right -= C.F.margin;
    }
    const reg = { x: x0, y: C.safe.y, w: right - x0, h: C.safe.h };
    const all = mid.concat(legal);
    const r = fitStack(all, C, reg, Object.assign({}, P, { gap: P.gap * 0.4 }), reg.h);
    r.placed.forEach((e) => { e.geometry.y += reg.y; });
    out.elements.push(...r.placed);
    return out;
  }

  function baseCand(view, C) {
    return { schema_version: "bancada-0.1", layout_id: view.layout_id, brand: view.brand, canvas: { width: C.W, height: C.H, background: view.canvas.background }, elements: [] };
  }

  // S2 — ancora e preenchimento: foto sangrada no canvas todo, textos numa banda com faixa
  B.S2 = function (view, fmtKey, P) {
    P = Object.assign({}, DEF, P);
    const C = ctx(view, fmtKey); const out = baseCand(view, C);
    const hero = view.elements.find(C.isHero);
    const blocks = flowOrder(view, C);
    if (C.W / C.H > 2.2) return B.S1(view, fmtKey, Object.assign({}, P, { heroFrac: 0.6 }));
    const r = fitStack(blocks, C, { x: C.safe.x, y: 0, w: C.safe.w, h: C.safe.h }, P, C.safe.h * 0.62);
    // lado da banda: semantico evita a area protegida; cego vai sempre para baixo
    let side = P.side;
    if (side === "auto") {
      if (C.blind || !hero) side = "bottom";
      else { const pc = protCenter(hero.asset); side = pc[1] > 0.5 ? "top" : "bottom"; }
    }
    const pad = Math.round(C.F.margin * 0.6);
    const bandH = r.used + 2 * pad;
    const y0 = side === "top" ? C.safe.y : C.safe.y + C.safe.h - r.used;
    r.placed.forEach((e) => { e.geometry.y += y0; });
    if (hero) {
      const focus = C.blind ? [0.5, 0.5] : protCenter(hero.asset);
      // o foco vai para o meio da parte livre
      const freeMid = side === "top" ? (y0 + r.used + C.H) / 2 / C.H : (y0 - pad) / 2 / C.H;
      out.elements.push(Object.assign(clone(hero), { geometry: { x: 0, y: 0, width: C.W, height: C.H, z: 1 }, crop: B.cover(hero.asset, C.W, C.H, focus, [0.5, C.blind ? 0.5 : freeMid], P.zoom) }));
    }
    const by = side === "top" ? 0 : y0 - pad;
    const bh = side === "top" ? y0 + r.used + pad : C.H - by;
    out.elements.push({ id: "faixa_auto", type: "SHAPE", role: "DECOR", priority: 0.1, geometry: { x: 0, y: by, width: C.W, height: bh, z: 2 }, style: { color: view.canvas.background, opacity: 0.86 } });
    out.elements.push(...r.placed.map((e) => { e.geometry.z = Math.max(5, e.geometry.z || 5); return e; }));
    return out;
  };

  // S3 — preservar estrutura: posicoes relativas da peca-mestra, reorientando colunas
  B.S3 = function (view, fmtKey, P) {
    P = Object.assign({}, DEF, P);
    const C = ctx(view, fmtKey); const out = baseCand(view, C);
    const sw = view.canvas.width, sh = view.canvas.height;
    const hero = view.elements.find(C.isHero);
    const bg = hero && area(box(hero)) > 0.8 * sw * sh;
    const items = view.elements.filter((e) => e.type !== "SHAPE" && !(bg && e === hero));
    // colunas por sobreposicao horizontal
    const cols = [];
    for (const e of [...items].sort((a, b) => a.geometry.x - b.geometry.x)) {
      const b = box(e);
      const c = cols.find((c) => Math.min(c.x + c.w, b.x + b.w) - Math.max(c.x, b.x) > 0.25 * Math.min(c.w, b.w));
      if (c) { const x = Math.min(c.x, b.x), X = Math.max(c.x + c.w, b.x + b.w); c.x = x; c.w = X - x; c.items.push(e); }
      else cols.push({ x: b.x, w: b.w, items: [e] });
    }
    const portrait = C.H / C.W > 0.9;
    let regions;
    if (portrait && cols.length > 1) {
      // empilha colunas: semantico poe primeiro a coluna com o elemento de maior prioridade
      if (!C.blind) cols.sort((a, b) => Math.max(...b.items.map((e) => e.priority)) - Math.max(...a.items.map((e) => e.priority)));
      const shares = cols.map((c) => c.items.some((e) => e === hero) ? P.heroFrac : (1 - P.heroFrac) / (cols.length - 1));
      let y = 0; regions = cols.map((c, i) => { const h = C.H * shares[i]; const r = { col: c, x: 0, y, w: C.W, h }; y += h; return r; });
    } else regions = cols.map((c) => ({ col: c, x: (c.x / sw) * C.W, y: 0, w: (c.w / sw) * C.W, h: C.H }));
    if (bg) {
      const focus = C.blind ? [0.5, 0.5] : protCenter(hero.asset);
      out.elements.push(Object.assign(clone(hero), { geometry: { x: 0, y: 0, width: C.W, height: C.H, z: 1 }, crop: B.cover(hero.asset, C.W, C.H, focus, [0.5, 0.5], P.zoom) }));
      for (const sh0 of view.elements.filter((e) => e.type === "SHAPE")) {
        const b = box(sh0); out.elements.push(Object.assign(clone(sh0), { geometry: { x: (b.x / sw) * C.W, y: (b.y / sh) * C.H, width: (b.w / sw) * C.W, height: (b.h / sh) * C.H, z: 2 } }));
      }
    }
    for (const R of regions) {
      const c = R.col;
      const ys = c.items.map((e) => e.geometry.y), Ys = c.items.map((e) => e.geometry.y + e.geometry.height);
      const cy0 = Math.min(...ys), cy1 = Math.max(...Ys);
      const inner = { x: Math.max(R.x, C.safe.x), y: Math.max(R.y, C.safe.y), w: Math.min(R.x + R.w, C.safe.x + C.safe.w) - Math.max(R.x, C.safe.x), h: Math.min(R.y + R.h, C.safe.y + C.safe.h) - Math.max(R.y, C.safe.y) };
      if (c.items.length === 1 && c.items[0] === hero) {
        const focus = C.blind ? [0.5, 0.5] : protCenter(hero.asset);
        out.elements.push(Object.assign(clone(hero), { geometry: { x: R.x, y: R.y, width: R.w, height: R.h, z: 1 }, crop: B.cover(hero.asset, R.w, R.h, focus, [0.5, 0.5], P.zoom) }));
        continue;
      }
      // dentro da coluna: mantem a ordem vertical e espaca proporcionalmente
      const blocks = c.items.filter((e) => e !== hero).sort((a, b) => a.geometry.y - b.geometry.y).map((e) => [e]);
      const r = fitStack(blocks, C, inner, P, inner.h);
      const slack = Math.max(0, inner.h - r.used);
      // distribui o espaco livre segundo a posicao relativa original do primeiro elemento
      const off = slack * clamp((cy0 / sh), 0, 1) * 0.6;
      r.placed.forEach((e) => { e.geometry.y += inner.y + off; });
      out.elements.push(...r.placed);
      if (c.items.includes(hero)) {
        const used = r.used;
        const hy = inner.y + off + used + C.H * 0.02;
        const hh = R.y + R.h - hy;
        if (hh > 40) out.elements.push(Object.assign(clone(hero), { geometry: { x: R.x, y: hy, width: R.w, height: hh, z: 1 }, crop: B.cover(hero.asset, R.w, hh, C.blind ? [0.5, 0.5] : protCenter(hero.asset), [0.5, 0.5], P.zoom) }));
      }
    }
    return out;
  };

  // A0 — letterbox: escala uniforme e centraliza (piso de sanidade do harness)
  B.A0 = function (view, fmtKey) {
    const F = B.formats[fmtKey];
    const s = Math.min(F.width / view.canvas.width, F.height / view.canvas.height);
    const ox = (F.width - view.canvas.width * s) / 2, oy = (F.height - view.canvas.height * s) / 2;
    const out = { schema_version: "bancada-0.1", layout_id: view.layout_id, brand: view.brand, canvas: { width: F.width, height: F.height, background: view.canvas.background }, elements: [] };
    for (const e of view.elements) {
      const n = clone(e), g = e.geometry;
      n.geometry = { x: ox + g.x * s, y: oy + g.y * s, width: g.width * s, height: g.height * s, z: g.z };
      if (n.type === "TEXT") n.style.size = Math.round(e.style.size * s * 100) / 100;
      out.elements.push(n);
    }
    return out;
  };

  // A1 — "resize": reposiciona proporcionalmente, escala uniforme nos objetos, recorta a foto para cobrir
  B.A1 = function (view, fmtKey) {
    const F = B.formats[fmtKey];
    const sx = F.width / view.canvas.width, sy = F.height / view.canvas.height, s = Math.min(sx, sy);
    const out = { schema_version: "bancada-0.1", layout_id: view.layout_id, brand: view.brand, canvas: { width: F.width, height: F.height, background: view.canvas.background }, elements: [] };
    for (const e of view.elements) {
      const n = clone(e), g = e.geometry;
      if (e.type === "IMAGE" && area(box(e)) > 0.15 * view.canvas.width * view.canvas.height) {
        n.geometry = { x: g.x * sx, y: g.y * sy, width: g.width * sx, height: g.height * sy, z: g.z };
        n.crop = B.cover(e.asset, n.geometry.width, n.geometry.height);
      } else if (e.type === "SHAPE") {
        n.geometry = { x: g.x * sx, y: g.y * sy, width: g.width * sx, height: g.height * sy, z: g.z };
      } else {
        const cx = (g.x + g.width / 2) * sx, cy = (g.y + g.height / 2) * sy;
        const w = e.type === "TEXT" ? Math.min(F.width - 2 * F.margin, g.width * sx) : g.width * s;
        const h = e.type === "TEXT" ? g.height * s * (g.width / Math.max(1, w / s)) : g.height * s;
        n.geometry = { x: clamp(cx - w / 2, 0, F.width - w), y: clamp(cy - h / 2, 0, F.height - h), width: w, height: h, z: g.z };
        if (n.type === "TEXT") {
          n.style.size = Math.round(e.style.size * s * 100) / 100;
          n.geometry.height = B.textHeight(n.text, n.style, w).h;
          n.geometry.y = clamp(cy - n.geometry.height / 2, 0, F.height - n.geometry.height);
        }
      }
      out.elements.push(n);
    }
    return out;
  };

  // aplica o "plano" de um agente (R8): so IDs/estrategias/parametros de um vocabulario fechado
  B.PLAN_VOCAB = {
    strategy: ["S1", "S2", "S3"], heroFrac: [0.3, 0.6], gap: [0.5, 1.6], tscale: [0.6, 1.4], align: ["left", "center"],
    side: ["auto", "top", "bottom", "left", "right"], zoom: [1, 1.6],
  };
  B.applyPlan = function (src, fmtKey, plan) {
    const V = B.PLAN_VOCAB; const errs = [];
    if (!V.strategy.includes(plan.strategy)) errs.push("strategy invalida");
    const P = {};
    for (const k of ["heroFrac", "gap", "tscale", "zoom"]) if (plan[k] != null) { if (plan[k] < V[k][0] || plan[k] > V[k][1]) errs.push(`${k} fora de [${V[k]}]`); P[k] = clamp(plan[k], V[k][0], V[k][1]); }
    for (const k of ["align", "side"]) if (plan[k] != null) { if (!V[k].includes(plan[k])) errs.push(`${k} invalido`); else P[k] = plan[k]; }
    const cand = B[V.strategy.includes(plan.strategy) ? plan.strategy : "S1"](src, fmtKey, P);
    return { cand, errs };
  };
})();

// T1 — template por formato: regioes declaradas uma vez por formato (padrao de medidas, P31/P33)
(function () {
  const B = window.B;
  const clone = (o) => JSON.parse(JSON.stringify(o));
  B.T1 = function (view, fmtKey, P) {
    P = Object.assign({ tscale: 1, gap: 1 }, P);
    const F = B.formats[fmtKey], T = F.template, W = F.width, H = F.height;
    const out = { schema_version: "bancada-0.1", layout_id: view.layout_id, brand: view.brand, canvas: { width: W, height: H, background: view.canvas.background }, elements: [] };
    const safe = { x: F.margin + F.safe[3], y: F.margin + F.safe[0], w: W - 2 * F.margin - F.safe[1] - F.safe[3], h: H - 2 * F.margin - F.safe[0] - F.safe[2] };
    const reg = (r, bleed) => {
      const R = { x: r[0] * W, y: r[1] * H, w: r[2] * W, h: r[3] * H };
      if (bleed) return R;
      const x = Math.max(R.x, safe.x), y = Math.max(R.y, safe.y);
      return { x, y, w: Math.min(R.x + R.w, safe.x + safe.w) - x, h: Math.min(R.y + R.h, safe.y + safe.h) - y };
    };
    const k = Math.sqrt((W * H) / (view.canvas.width * view.canvas.height));
    const mf = (e) => F.min_font[e.role] || F.min_font.OTHER;
    const lmin = (F.logo_min_width || {})[view.brand] || 100;
    const hero = view.elements.find((e) => e.role === "HERO");
    const logo = view.elements.find((e) => e.role === "LOGO");
    const head = view.elements.find((e) => e.role === "HEADLINE");
    const legal = view.elements.find((e) => e.role === "LEGAL");
    const others = view.elements.filter((e) => e.type !== "SHAPE" && ![hero, logo, head, legal].includes(e));
    function fill(items, R, align, maxIter = 16) {
      let sc = P.tscale, placed, used;
      for (let it = 0; it < maxIter; it++) {
        placed = []; let y = R.y; const gap = Math.round(H * 0.018 * P.gap);
        // pares icone+rotulo viram linha
        const done = new Set();
        for (const e of items) {
          if (done.has(e.id)) continue;
          if (e.type === "IMAGE" && e.role !== "LOGO") {
            const lbl = items.find((t) => t.type === "TEXT" && (view.relations || []).some((r) => r.source === t.id && r.target === e.id));
            const a = B.assets[e.asset]; const iw = Math.min(R.w * 0.18, Math.max(48, e.geometry.width * k * sc)); const ih = iw * a.height / a.width;
            let rowH = ih; let tt = null;
            if (lbl) {
              const st = Object.assign({}, lbl.style, { size: Math.max(mf(lbl), Math.round(lbl.style.size * k * sc)), align: "left" });
              const m = B.textHeight(lbl.text, st, R.w - iw - gap);
              tt = Object.assign(clone(lbl), { style: st, geometry: { x: R.x + iw + gap, y, width: R.w - iw - gap, height: m.h, z: 5 } });
              rowH = Math.max(ih, m.h); tt.geometry.y = y + (rowH - m.h) / 2; done.add(lbl.id);
            }
            placed.push(Object.assign(clone(e), { geometry: { x: R.x, y: y + (rowH - ih) / 2, width: iw, height: ih, z: 4 }, crop: [0, 0, 1, 1] }));
            if (tt) placed.push(tt);
            y += rowH + gap; done.add(e.id); continue;
          }
          if (e.type === "IMAGE") { // logo
            const a = B.assets[e.asset]; let w = Math.max(lmin, Math.min(R.w * 0.45, e.geometry.width * k * sc)); let h = w * a.height / a.width;
            if (h > R.h * 0.5) { h = R.h * 0.5; w = Math.max(lmin, h * a.width / a.height); h = w * a.height / a.width; }
            const x = align === "center" ? R.x + (R.w - w) / 2 : R.x;
            placed.push(Object.assign(clone(e), { geometry: { x, y, width: w, height: h, z: 6 }, crop: [0, 0, 1, 1] }));
            y += h + gap; done.add(e.id); continue;
          }
          const st = Object.assign({}, e.style, { size: Math.max(mf(e), Math.round(e.style.size * k * sc)), align });
          const m = B.textHeight(e.text, st, R.w);
          placed.push(Object.assign(clone(e), { style: st, geometry: { x: R.x, y, width: R.w, height: m.h, z: 5 } }));
          y += m.h + gap; done.add(e.id);
        }
        used = y - R.y - gap;
        if (used <= R.h) break;
        sc *= 0.9;
      }
      return { placed, used };
    }
    if (hero) { const R = reg(T.hero, true); out.elements.push(Object.assign(clone(hero), { geometry: { x: R.x, y: R.y, width: R.w, height: R.h, z: 1 }, crop: B.cover(hero.asset, R.w, R.h, [hero && B.assets[hero.asset].protected[0] + B.assets[hero.asset].protected[2] / 2, B.assets[hero.asset].protected[1] + B.assets[hero.asset].protected[3] / 2]) })); }
    const topItems = T.logo ? [head] : [logo, head];
    const t = fill(topItems.filter(Boolean), reg(T.top), T.align); out.elements.push(...t.placed);
    if (T.logo && logo) { const r = fill([logo], reg(T.logo), "center"); out.elements.push(...r.placed); }
    const m = fill(others, reg(T.mid), T.align); out.elements.push(...m.placed);
    if (legal) { const r = fill([legal], reg(T.legal), T.align); out.elements.push(...r.placed); }
    return out;
  };
})();
