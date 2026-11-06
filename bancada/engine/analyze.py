"""Consolida a rodada: QA automatico + juri cego + custo + variancia + segunda marca.

Uso: analyze.py <run> <chave_do_juri.json>  -> runs/<run>/analysis.json e analysis.md
"""
import json, os, sys, glob, itertools, collections, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
run, keyfile = sys.argv[1], sys.argv[2]
B = os.path.join(ROOT, "runs", run)
R = [r for r in json.load(open(os.path.join(B, "results.json"))) if "error" not in r]
errors = [r for r in json.load(open(os.path.join(B, "results.json"))) if "error" in r]
key = json.load(open(keyfile))
usage = json.load(open(os.path.join(B, "usage.json")))
MAIN = ["A0", "A1", "B0", "T1", "R1", "R1opt", "R8", "R3", "R2"]
NAMES = {"A0": "letterbox (piso)", "A1": "resize proporcional", "B0": "reflow cego (sem semântica)",
         "T1": "template por formato", "R1": "R1 motor semântico", "R1opt": "R1 + otimização",
         "R8": "R8 IA escolhe, código posiciona", "R3": "R3 IA posiciona direto", "R2": "R2 IA escreve script por job",
         "R8b": "R8 réplica", "R3b": "R3 réplica"}
BRAND = lambda L: L.split("_")[0]
res = {(r["arm"], r["layout"], r["format"]): r for r in R}
layouts = sorted({r["layout"] for r in R})
fmts = ["email_600x1200", "post_1080x1350", "card_1080x1080", "stories_1080x1920", "banner_970x250"]
arms = [a for a in MAIN + ["R8b", "R3b"] if any(k[0] == a for k in res)]

# ------------------------------------------------------------- juri
J = []  # (persona, layout, format, arm, rank_norm, ship, reason)
for f in glob.glob(os.path.join(B, "judgments", "*", "*.json")):
    persona = os.path.basename(os.path.dirname(f))
    try:
        d = json.load(open(f))
    except Exception:
        continue
    L = d.get("layout") or os.path.basename(f)[:-5]
    for fmt, v in d.get("formats", {}).items():
        k = key.get(f"{L}__{fmt}", {})
        rank = v.get("ranking", [])
        n = len(rank)
        for i, let in enumerate(rank):
            if let not in k:
                continue
            J.append({"persona": persona, "layout": L, "format": fmt, "arm": k[let], "rank_norm": i / max(1, n - 1),
                      "ship": bool(v.get("ship", {}).get(let, False)), "reason": v.get("reasons", {}).get(let, "")})
jb = collections.defaultdict(list)
for j in J:
    jb[(j["arm"], j["layout"], j["format"])].append(j)

summary = {}
for a in arms:
    rows = [res[(a, L, f)] for L in layouts for f in fmts if (a, L, f) in res]
    js = [j for j in J if j["arm"] == a]
    acc = 0; acc_n = 0
    for L in layouts:
        for f in fmts:
            r = res.get((a, L, f))
            if not r:
                continue
            jj = jb.get((a, L, f), [])
            if jj:
                acc_n += 1
                if r["eligible"] and sum(x["ship"] for x in jj) * 2 > len(jj):
                    acc += 1
    s = {"name": NAMES.get(a, a), "n": len(rows),
         "elegiveis": sum(r["eligible"] for r in rows),
         "falhas_media": round(st.mean(r["fails"] for r in rows), 2) if rows else None,
         "nota_suave": round(st.mean(r["soft_score"] for r in rows), 3) if rows else None,
         "juri_n": len(js),
         "juri_nota": round(1 - st.mean(j["rank_norm"] for j in js), 3) if js else None,
         "juri_enviaria": round(sum(j["ship"] for j in js) / len(js), 3) if js else None,
         "aceitavel": acc, "aceitavel_n": acc_n}
    for br in ("bioma", "otium"):
        rb = [r for r in rows if BRAND(r["layout"]) == br]
        jbx = [j for j in js if BRAND(j["layout"]) == br]
        s[f"elegiveis_{br}"] = f"{sum(r['eligible'] for r in rb)}/{len(rb)}"
        s[f"enviaria_{br}"] = round(sum(j["ship"] for j in jbx) / len(jbx), 3) if jbx else None
    s["por_formato"] = {f: {"elegiveis": sum(res[(a, L, f)]["eligible"] for L in layouts if (a, L, f) in res),
                            "enviaria": (lambda x: round(sum(j["ship"] for j in x) / len(x), 2) if x else None)([j for j in js if j["format"] == f])}
                        for f in fmts}
    u = [v for k, v in usage.items() if k.split("/")[0] == a]
    if u:
        s["custo_tokens_por_peca"] = round(sum(x["tokens"] for x in u) / (5 * len(u)))
        s["tempo_s_por_peca"] = round(sum(x["ms"] for x in u) / (5 * len(u)) / 1000, 1)
    else:
        ms = [r.get("ms") or 0 for r in rows]
        s["custo_tokens_por_peca"] = 0
        s["tempo_s_por_peca"] = round(st.mean(ms) / 1000, 3) if ms else None
    summary[a] = s

# ------------------------------------------------------------- confronto par a par (mesmo jurado, mesma adaptacao)
pair = {}
for a, b in itertools.permutations([x for x in MAIN if x in arms], 2):
    w = t = 0
    for (persona, L, f), grp in itertools.groupby(sorted(J, key=lambda j: (j["persona"], j["layout"], j["format"])), key=lambda j: (j["persona"], j["layout"], j["format"])):
        g = {j["arm"]: j["rank_norm"] for j in grp}
        if a in g and b in g:
            t += 1; w += g[a] < g[b]
    pair[f"{a}>{b}"] = round(w / t, 3) if t else None

# ------------------------------------------------------------- regra de parada da auditoria: semantico x cego, pareado por adaptacao
def mean_rank(a, L, f):
    x = jb.get((a, L, f)); return st.mean(j["rank_norm"] for j in x) if x else None
def acceptable(a, L, f):
    r = res.get((a, L, f)); x = jb.get((a, L, f), [])
    return bool(r and r["eligible"] and x and sum(j["ship"] for j in x) * 2 > len(x))
def paired(a, b):
    wins = ties = losses = 0
    for L in layouts:
        for f in fmts:
            ra, rb = mean_rank(a, L, f), mean_rank(b, L, f)
            if ra is None or rb is None:
                continue
            ea, eb = acceptable(a, L, f), acceptable(b, L, f)
            if ea and not eb: wins += 1
            elif eb and not ea: losses += 1
            elif ra < rb - 1e-9: wins += 1
            elif rb < ra - 1e-9: losses += 1
            else: ties += 1
    return {"vitorias": wins, "empates": ties, "derrotas": losses}
confrontos = {k: paired(*k.split(" x ")) for k in ["R1 x B0", "R8 x R1", "R8 x R3", "R8 x T1", "R1opt x R1", "R3 x R2", "R8 x R2", "T1 x R1"]
              if all(x in arms for x in k.split(" x "))}

# ------------------------------------------------------------- variancia entre replicas (mesma peca, outro agente)
var = {}
for a, b in (("R8", "R8b"), ("R3", "R3b")):
    same_e = n = 0; plans_same = 0; dsoft = []
    for L in layouts:
        for f in fmts:
            if (a, L, f) in res and (b, L, f) in res:
                n += 1
                same_e += res[(a, L, f)]["eligible"] == res[(b, L, f)]["eligible"]
                dsoft.append(abs(res[(a, L, f)]["soft_score"] - res[(b, L, f)]["soft_score"]))
                if a == "R8":
                    try:
                        pa = json.load(open(os.path.join(B, "candidates", a, f"{L}__{f}.json"))).get("_plan", {})
                        pb = json.load(open(os.path.join(B, "candidates", b, f"{L}__{f}.json"))).get("_plan", {})
                        plans_same += pa.get("strategy") == pb.get("strategy")
                    except Exception:
                        pass
    if n:
        var[f"{a} x {b}"] = {"adaptacoes": n, "mesma_elegibilidade": f"{same_e}/{n}", "dif_media_nota_suave": round(st.mean(dsoft), 3),
                             **({"mesma_estrategia": f"{plans_same}/{n}"} if a == "R8" else {})}

# ------------------------------------------------------------- integridade do R8: o candidato e exatamente a saida do plano?
falhas = collections.Counter()
for r in R:
    for h in r["hard"]:
        if h["status"] == "FAIL":
            falhas[(r["arm"], h["check"])] += 1
top_falhas = {a: dict(collections.Counter({c: v for (x, c), v in falhas.items() if x == a}).most_common(4)) for a in arms}

out = {"resumo": summary, "par_a_par": pair, "confrontos": confrontos, "variancia": var, "falhas_mais_comuns": top_falhas,
       "erros_de_render": errors, "n_julgamentos": len(J), "jurados": sorted({j["persona"] for j in J})}
json.dump(out, open(os.path.join(B, "analysis.json"), "w"), indent=1, ensure_ascii=False)

# ------------------------------------------------------------- markdown
L_ = ["# Rodada " + run, "", f"{len(R)} adaptações verificadas · {len(J)} julgamentos cegos · jurados: {', '.join(out['jurados'])}", "",
      "| Braço | Passa no QA | Júri: nota (0–1) | Júri: enviaria | Aceitável¹ | Bioma QA | OTIUM QA | Tokens/peça | s/peça |",
      "|---|---|---|---|---|---|---|---|---|"]
for a in arms:
    s = summary[a]
    L_.append(f"| {s['name']} | {s['elegiveis']}/{s['n']} | {s['juri_nota'] if s['juri_nota'] is not None else '–'} | "
              f"{'' if s['juri_enviaria'] is None else str(round(100*s['juri_enviaria']))+'%'} | {s['aceitavel']}/{s['aceitavel_n']} | "
              f"{s['elegiveis_bioma']} | {s['elegiveis_otium']} | {s['custo_tokens_por_peca']:,} | {s['tempo_s_por_peca']} |")
L_ += ["", "¹ Aceitável = passa em todas as verificações duras **e** a maioria dos jurados mandaria ao cliente sem retoque estrutural.", "",
       "## Confrontos pareados (mesma adaptação)", "", "| Confronto | Vitórias | Empates | Derrotas |", "|---|---|---|---|"]
for k, v in confrontos.items():
    L_.append(f"| {k} | {v['vitorias']} | {v['empates']} | {v['derrotas']} |")
L_ += ["", "## Variância entre réplicas", ""] + [f"- {k}: {json.dumps(v, ensure_ascii=False)}" for k, v in var.items()]
L_ += ["", "## Por formato (elegíveis / % enviaria)", "", "| Braço | " + " | ".join(fmts) + " |", "|---|" + "---|" * len(fmts)]
for a in arms:
    pf = summary[a]["por_formato"]
    L_.append(f"| {a} | " + " | ".join(f"{pf[f]['elegiveis']}/6 · {'' if pf[f]['enviaria'] is None else str(round(100*pf[f]['enviaria']))+'%'}" for f in fmts) + " |")
L_ += ["", "## Falhas duras mais comuns", ""] + [f"- **{a}**: {v}" for a, v in top_falhas.items() if v]
open(os.path.join(B, "analysis.md"), "w").write("\n".join(L_) + "\n")
print("\n".join(L_))
