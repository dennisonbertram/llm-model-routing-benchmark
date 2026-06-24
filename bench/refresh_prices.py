"""Refresh registry.json prices from the live OpenRouter catalog (run before an overnight benchmark
so costs are current). OpenRouter models only; direct OpenAI ids (gpt-*) are left untouched.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 refresh_prices.py
"""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(__file__)
reg = json.load(open(os.path.join(HERE, "registry.json")))
key = os.environ["OPENROUTER_API_KEY"]
req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {key}"})
cat = {m["id"]: m for m in json.loads(urllib.request.urlopen(req, timeout=30).read())["data"]}
changed = 0
for m in reg["models"]:
    if not m["id"].startswith("openrouter/"):
        continue
    real = m["id"][len("openrouter/"):]
    if real in cat:
        p = cat[real]["pricing"]
        nin, nout = round(float(p["prompt"]) * 1e6, 4), round(float(p["completion"]) * 1e6, 4)
        if (nin, nout) != (m["in"], m["out"]):
            print(f"  {m['id']}: ${m['in']}/${m['out']} -> ${nin}/${nout}")
            m["in"], m["out"] = nin, nout
            changed += 1
    else:
        print(f"  WARNING: {m['id']} not in OpenRouter catalog")
json.dump(reg, open(os.path.join(HERE, "registry.json"), "w"), indent=2)
print(f"updated {changed} prices")
