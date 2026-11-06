// Executor da bancada (Node + Playwright/Chromium).
//   node engine/bench.mjs engine <run> [arms] [layouts] [formats]  -> gera candidatos dos motores deterministicos
//   node engine/bench.mjs eval <run>                                -> renderiza e verifica todos os candidatos do run
//   node engine/bench.mjs check <candidate.json> [out.png]          -> ferramenta dos agentes: render + verificacao
//   node engine/bench.mjs plan <layout> <format> '<json do plano>' <out.json>  -> R8: aplica plano de vocabulario fechado
//   node engine/bench.mjs source                                     -> renderiza as pecas-mestras
import { createRequire } from "module";
const { chromium } = createRequire(import.meta.url)("playwright");
import fs from "fs";
import path from "path";
import { execFileSync } from "child_process";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const P = (...a) => path.join(ROOT, ...a);
const readJ = (f) => JSON.parse(fs.readFileSync(f, "utf8"));
const writeJ = (f, o) => { fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, JSON.stringify(o, null, 1)); };

const ASSETS = readJ(P("assets/assets.json"));
const FORMATS = readJ(P("fixtures/formats.json"));
const LAYOUTS = fs.readdirSync(P("fixtures")).filter((f) => f !== "formats.json" && f.endsWith(".json")).map((f) => f.replace(".json", ""));
const src = (id) => readJ(P("fixtures", id + ".json"));

async function openPage() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 2000, height: 2000 } });
  const html = `<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="${P("fonts/fonts.css")}"><style>body{margin:0;background:#888}</style></head><body><div id="stage"></div></body></html>`;
  const tmp = P("engine/.page.html");
  fs.writeFileSync(tmp, html.replace(P("fonts/fonts.css"), "../fonts/fonts.css"));
  await page.goto("file://" + tmp);
  await page.addScriptTag({ path: P("engine/lib.js") });
  await page.evaluate(({ a, f, base }) => { B.assets = a; B.formats = f; B.assetBase = base; }, { a: ASSETS, f: FORMATS, base: "../assets/" });
  // forca carregar todas as fontes usadas
  await page.evaluate(async () => {
    const fams = ["Cormorant Garamond", "Barlow", "Inter", "Archivo", "Host Grotesk", "Poppins"];
    await Promise.all(fams.flatMap((f) => ["400", "500", "600", "700"].map((w) => document.fonts.load(`${w} 20px '${f}'`))));
  });
  return { browser, page };
}

// renderiza a peca-mestra para obter medicoes de referencia (fidelidade)

async function setSource(page, s) {
  await page.evaluate((ir) => { B.render(ir); }, s);
  await page.evaluate(() => B.ready());
  await page.evaluate((ir) => {
    B._srcMeas = B.measure(ir);
    // visibilidade da area protegida na peca-mestra (o minimo exigido e relativo a ela)
    const fake = Object.assign({}, B.formats); B.formats.__src = { width: ir.canvas.width, height: ir.canvas.height, margin: 0, safe: [0, 0, 0, 0], min_font: { OTHER: 0 }, logo_min_width: {} };
    B._srcVis = 1;
    const r = B.checks(ir, ir, "__src", B._srcMeas);
    B._srcVis = r.protected_visible;
    delete B.formats.__src;
  }, s);
}

async function evalCandidate(page, s, cand, fmtKey, png) {
  await page.evaluate((ir) => { B.render(ir); }, cand);
  await page.evaluate(() => B.ready());
  const meas = await page.evaluate((ir) => B.measure(ir), cand);
  const res = await page.evaluate(({ s, c, f, m }) => B.checks(s, c, f, m), { s, c: cand, f: fmtKey, m: meas });
  if (png) {
    fs.mkdirSync(path.dirname(png), { recursive: true });
    await page.locator("#root").screenshot({ path: png });
    // segunda captura sem o texto: fundo real para o contraste
    await page.evaluate(() => { for (const d of document.querySelectorAll("#root [data-id]")) if (d.childNodes.length && d.firstChild.nodeType === 3) d.style.color = "transparent"; });
    await page.locator("#root").screenshot({ path: png.replace(/\.png$/, ".bg.png") });
  }
  return { meas, res };
}

function pixelChecks(candFile, measFile, png, srcFile) {
  const out = execFileSync("python3", [P("engine/pixel.py"), candFile, measFile, png, srcFile], { encoding: "utf8" });
  return JSON.parse(out);
}

function score(res, pix) {
  const fails = res.fails + (pix ? pix.fails : 0);
  return { eligible: fails === 0, fails, soft: res.soft_score };
}

const ENGINE_ARMS = {
  A0: (p, s, f) => p.evaluate(({ s, f }) => B.A0(s, f), { s, f }),
  A1: (p, s, f) => p.evaluate(({ s, f }) => B.A1(s, f), { s, f }),
};

async function bestOf(page, s, view, f, strategies, paramsList) {
  // melhor de k: mesmo k para cego e semantico (achado C-03). Selecao so por verificacoes geometricas.
  let best = null, tried = [];
  for (const st of strategies) for (const prm of paramsList) {
    const cand = await page.evaluate(({ v, f, st, prm }) => B[st](v, f, prm), { v: view, f, st, prm });
    // o candidato do braco cego carrega os papeis "OTHER"; devolve os dados da peca-mestra (o render e o mesmo)
    cand.elements = cand.elements.map((e) => { const o = s.elements.find((x) => x.id === e.id); return o ? Object.assign({}, e, { role: o.role, priority: o.priority }) : e; });
    const { res } = await evalCandidate(page, s, cand, f, null);
    const sc = [res.fails, -res.soft_score];
    tried.push({ strategy: st, params: prm, fails: res.fails, soft: res.soft_score });
    if (!best || sc[0] < best.sc[0] || (sc[0] === best.sc[0] && sc[1] < best.sc[1])) best = { cand, sc, st, prm };
  }
  best.cand._provenance = { strategy: best.st, params: best.prm, tried };
  return best.cand;
}

async function optimize(page, s, f, start, iters = 40, seed = 1) {
  // R1opt: busca local estilo O'Donovan (energia = falhas, depois nota suave) sobre os parametros
  let rnd = seed; const R = () => ((rnd = (rnd * 16807) % 2147483647) / 2147483647);
  const base = start._provenance;
  let best = { cand: start, fails: base.tried.find((t) => t.strategy === base.strategy && JSON.stringify(t.params) === JSON.stringify(base.params)).fails, soft: 0 };
  { const { res } = await evalCandidate(page, s, start, f, null); best.fails = res.fails; best.soft = res.soft_score; }
  let cur = Object.assign({ heroFrac: 0.45, gap: 1, tscale: 1, align: "left", side: "auto", zoom: 1 }, base.params);
  let st = base.strategy;
  for (let i = 0; i < iters; i++) {
    const p = Object.assign({}, cur);
    const k = Math.floor(R() * 6);
    if (k === 0) p.heroFrac = Math.min(0.6, Math.max(0.3, p.heroFrac + (R() - 0.5) * 0.12));
    if (k === 1) p.gap = Math.min(1.6, Math.max(0.5, p.gap + (R() - 0.5) * 0.4));
    if (k === 2) p.tscale = Math.min(1.4, Math.max(0.6, p.tscale + (R() - 0.5) * 0.2));
    if (k === 3) p.align = R() < 0.5 ? "left" : "center";
    if (k === 4) p.side = ["auto", "top", "bottom"][Math.floor(R() * 3)];
    if (k === 5) p.zoom = Math.min(1.6, Math.max(1, p.zoom + (R() - 0.5) * 0.2));
    const s2 = R() < 0.15 ? ["S1", "S2", "S3"][Math.floor(R() * 3)] : st;
    const cand = await page.evaluate(({ v, f, st, prm }) => B[st](v, f, prm), { v: s, f, st: s2, prm: p });
    const { res } = await evalCandidate(page, s, cand, f, null);
    if (res.fails < best.fails || (res.fails === best.fails && res.soft_score > best.soft)) { best = { cand, fails: res.fails, soft: res.soft_score }; cur = p; st = s2; }
  }
  best.cand._provenance = { strategy: st, params: cur, optimized_from: base.strategy, iters };
  return best.cand;
}

async function cmdEngine(run, arms, layouts, formats) {
  const { browser, page } = await openPage();
  const grid = [{}, { heroFrac: 0.38 }, { heroFrac: 0.52, align: "center" }];
  for (const L of layouts) {
    const s = src(L);
    await setSource(page, s);
    const blind = await page.evaluate((s) => B.blindView(s), s);
    for (const f of formats) {
      for (const arm of arms) {
        const t0 = Date.now();
        let cand;
        if (ENGINE_ARMS[arm]) cand = await ENGINE_ARMS[arm](page, s, f);
        else if (arm === "B0") cand = await bestOf(page, s, blind, f, ["S1", "S2", "S3"], grid);
        else if (arm === "R1") cand = await bestOf(page, s, s, f, ["S1", "S2", "S3"], grid);
        else if (arm === "R1opt") { const st = await bestOf(page, s, s, f, ["S1", "S2", "S3"], grid); await setSource(page, s); cand = await optimize(page, s, f, st, 45); }
        else if (arm === "T1") cand = await page.evaluate(({ s, f }) => B.T1(s, f), { s, f });
        else throw new Error("braco desconhecido " + arm);
        await setSource(page, s);
        cand._arm = arm; cand._ms = Date.now() - t0;
        writeJ(P("runs", run, "candidates", arm, `${L}__${f}.json`), cand);
        process.stdout.write(`${arm} ${L} ${f} ${cand._ms}ms\n`);
      }
    }
  }
  await browser.close();
}

async function cmdEval(run) {
  const { browser, page } = await openPage();
  const base = P("runs", run, "candidates");
  const results = [];
  for (const arm of fs.readdirSync(base)) {
    for (const fn of fs.readdirSync(path.join(base, arm)).filter((x) => x.endsWith(".json"))) {
      const [L, f] = fn.replace(".json", "").split("__");
      const s = src(L);
      await setSource(page, s);
      let cand;
      try { cand = readJ(path.join(base, arm, fn)); } catch (e) { results.push({ arm, layout: L, format: f, error: "json invalido" }); continue; }
      const png = P("runs", run, "renders", arm, `${L}__${f}.png`);
      let out;
      try { out = await evalCandidate(page, s, cand, f, png); } catch (e) { results.push({ arm, layout: L, format: f, error: String(e).slice(0, 200) }); continue; }
      const mf = P("runs", run, "checks", arm, `${L}__${f}.meas.json`);
      writeJ(mf, out.meas);
      const pix = pixelChecks(path.join(base, arm, fn), mf, png, P("fixtures", L + ".json"));
      const all = { arm, layout: L, format: f, eligible: out.res.fails + pix.fails === 0, fails: out.res.fails + pix.fails,
        hard: out.res.hard.concat(pix.hard), soft: Object.assign({}, out.res.soft, pix.soft), soft_score: out.res.soft_score,
        protected_visible: out.res.protected_visible, ms: cand._ms, provenance: cand._provenance || null };
      writeJ(P("runs", run, "checks", arm, `${L}__${f}.json`), all);
      results.push(all);
      process.stdout.write(`${arm} ${L} ${f} ${all.eligible ? "ELEGIVEL" : "INELEGIVEL(" + all.fails + ")"} soft=${all.soft_score.toFixed(3)}\n`);
    }
  }
  writeJ(P("runs", run, "results.json"), results);
  await browser.close();
}

async function cmdCheck(file, png) {
  const cand = readJ(file);
  const L = cand.layout_id; const f = cand._format || path.basename(file).replace(".json", "").split("__")[1];
  if (!FORMATS[f]) throw new Error("formato desconhecido: " + f);
  const s = src(L);
  const { browser, page } = await openPage();
  await setSource(page, s);
  png = png || file.replace(/\.json$/, ".png");
  const out = await evalCandidate(page, s, cand, f, png);
  const mf = file.replace(/\.json$/, ".meas.json");
  writeJ(mf, out.meas);
  const pix = pixelChecks(file, mf, png, P("fixtures", L + ".json"));
  fs.unlinkSync(mf);
  await browser.close();
  const hard = out.res.hard.concat(pix.hard);
  console.log(JSON.stringify({ eligible: out.res.fails + pix.fails === 0, fails: out.res.fails + pix.fails, hard, soft: Object.assign({}, out.res.soft, pix.soft), soft_score: Math.round(out.res.soft_score * 1000) / 1000, text_measured: out.meas, png }, null, 1));
}

async function cmdPlan(L, f, planJson, outFile) {
  const s = src(L);
  const { browser, page } = await openPage();
  await setSource(page, s);
  const plan = JSON.parse(planJson);
  const { cand, errs } = await page.evaluate(({ s, f, plan }) => B.applyPlan(s, f, plan), { s, f, plan });
  cand._plan = plan; cand._format = f;
  writeJ(outFile, cand);
  await browser.close();
  console.log(JSON.stringify({ written: outFile, plan_errors: errs }));
}

async function cmdSource() {
  const { browser, page } = await openPage();
  for (const L of LAYOUTS) {
    const s = src(L);
    await page.evaluate((ir) => B.render(ir), s);
    await page.evaluate(() => B.ready());
    await page.locator("#root").screenshot({ path: P("fixtures", "renders", L + ".png") });
  }
  await browser.close();
}

const [cmd, ...a] = process.argv.slice(2);
const list = (x, all) => (!x || x === "all" ? all : x.split(","));
if (cmd === "engine") await cmdEngine(a[0], list(a[1], ["A0", "A1", "B0", "R1", "R1opt", "T1"]), list(a[2], LAYOUTS), list(a[3], Object.keys(FORMATS)));
else if (cmd === "eval") await cmdEval(a[0]);
else if (cmd === "check") await cmdCheck(a[0], a[1]);
else if (cmd === "plan") await cmdPlan(a[0], a[1], a[2], a[3]);
else if (cmd === "source") { fs.mkdirSync(P("fixtures/renders"), { recursive: true }); await cmdSource(); }
else console.log("uso: engine|eval|check|plan|source");
