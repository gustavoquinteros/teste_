"""Registra custo de um agente gerador: usage.py <arm> <layout> <tokens> <tool_uses> <ms>"""
import json, sys, os
p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs", "R01", "usage.json")
u = json.load(open(p))
a, L, t, n, ms = sys.argv[1:6]
u[f"{a}/{L}"] = {"tokens": int(t), "tool_uses": int(n), "ms": int(ms)}
json.dump(u, open(p, "w"), indent=1)
