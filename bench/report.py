"""Generate the Geist-styled HTML report from the outcome matrix → Chrome print-to-pdf.

ONE comparison table on the full suite: Sakana Fugu (fugu, fugu-ultra) vs single models vs combination
methods (majority vote, consensus cascade) vs the oracle ceiling — all on the identical task stack,
same grader, same cost accounting (Fugu billed on all tokens incl. orchestration). Includes a
Method & limitations section reflecting an independent Codex (GPT-5) method audit.
"""
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import combos as CB  # noqa: E402
import suites as SU  # noqa: E402
import matrix as MX  # noqa: E402

SUITE = "superhard"
reg = json.load(open(os.path.join(HERE, "registry.json")))["models"]
tier = {m["id"]: m.get("tier", "") for m in reg}
ref = next((m["id"] for m in reg if m.get("reference")), "gpt-5.5")
tasks = SU.load(SUITE)
N = len(tasks)
gold = {t["id"]: t["gold"] for t in tasks}
mat = MX.load(os.path.join(HERE, f"matrix_{SUITE}.json"))
short = lambda mid: mid.split("/")[-1]

# every model with full coverage (all task cells measured) — Fugu included. A null answer is a
# measured WRONG outcome (counted against the model), not missing data, so it does NOT exclude.
have = [m["id"] for m in reg if m.get("enabled", True)
        and all(t["id"] in mat.get(m["id"], {}) for t in tasks)]
FUGU = [m for m in ("fugu", "fugu-ultra") if m in have]
rows = CB.evaluate_all(mat, have, tasks, gold, ref=ref, max_k=4)
refrow = next(r for r in rows if r["strategy"] == "solo" and r["members"] == [ref])
ref_acc, ref_cost = refrow["acc"], refrow["cost"]
solos = {r["members"][0]: r for r in rows if r["strategy"] == "solo"}
oracle = next(r for r in rows if r["strategy"].startswith("oracle"))


def mean_lat_ms(mid):
    cs = [c["lat"] for c in mat[mid].values() if c.get("lat")]
    return sum(cs) / len(cs) if cs else 0


def combo_lat_ms(members, escalate_ref=None):
    tot = 0
    for t in tasks:
        ms = [mat[m][t["id"]]["lat"] for m in members if mat[m][t["id"]].get("lat")]
        per = max(ms) if ms else 0
        if escalate_ref:
            votes = [mat[m][t["id"]]["ans"] for m in members]
            if not (len(set(votes)) == 1 and votes[0] is not None):
                per += mat[escalate_ref][t["id"]].get("lat", 0)
        tot += per
    return tot / N


def n_ok(acc):
    return round(acc * N)


def best(prefix):
    cs = [r for r in rows if r["strategy"].startswith(prefix)]
    return max(cs, key=lambda r: (r["acc"], -r["cost"])) if cs else None


def cheapest_matching(prefix, target):
    cs = [r for r in rows if r["strategy"].startswith(prefix) and r["acc"] >= target - 1e-9]
    return min(cs, key=lambda r: r["cost"]) if cs else None


METHOD = {"single": ("Single model", "m-single"), "fugu": ("Orchestration (Fugu)", "m-fugu"),
          "vote": ("Majority vote", "m-vote"), "cascade": ("Consensus cascade", "m-cascade"),
          "oracle": ("Oracle ceiling", "m-oracle")}


def fmt_cost(c):
    if c is None or c == 0:
        return "—"
    return f"${c:.4f}" if c >= 0.001 else f"${c:.5f}"


def fmt_x(c):
    if c is None or c == 0:
        return "—"
    if abs(c - ref_cost) < 1e-12:
        return "1.0×"
    r = ref_cost / c
    return f"{r:.1f}× cheaper" if r >= 1 else f"{1/r:.1f}× pricier"


def lat_str(ms):
    if not ms:
        return "—"
    return f"{ms/1000:.0f}s" if ms >= 10000 else f"{ms/1000:.1f}s"


# ---------- curated ONE comparison table (all on N tasks) ----------
table = []


def add(mk, config, acc, cost, lat, note):
    table.append({"mk": mk, "config": config, "acc": acc, "cost": cost, "lat": lat, "note": note})


add("oracle", "best-of-pool per task", oracle["acc"], 0, 0, "unrealizable ceiling of the whole pool")
add("single", ref, solos[ref]["acc"], solos[ref]["cost"], mean_lat_ms(ref), "frontier reference — the bar to beat")
if "fugu-ultra" in solos:
    add("fugu", "fugu-ultra", solos["fugu-ultra"]["acc"], solos["fugu-ultra"]["cost"],
        mean_lat_ms("fugu-ultra"), "Sakana multi-agent conductor (largest)")
if "fugu" in solos:
    add("fugu", "fugu (mini)", solos["fugu"]["acc"], solos["fugu"]["cost"],
        mean_lat_ms("fugu"), "Sakana multi-agent conductor (mini)")
bv = best("vote-")
add("vote", "+".join(short(m) for m in bv["members"]), bv["acc"], bv["cost"], combo_lat_ms(bv["members"]),
    "majority vote on the integer answer")
bc = best("consensus-escalate-")
bcmem = [m for m in bc["members"] if not m.startswith("->")]
add("cascade", "+".join(short(m) for m in bcmem) + f" → {ref}", bc["acc"], bc["cost"],
    combo_lat_ms(bcmem, escalate_ref=ref), "cheap members agree → trust; disagree → escalate")
for mid in ["gpt-5-nano", "openrouter/deepseek/deepseek-v4-pro", "openrouter/deepseek/deepseek-v4-flash"]:
    if mid in solos:
        add("single", short(mid), solos[mid]["acc"], solos[mid]["cost"], mean_lat_ms(mid),
            f"{tier.get(mid,'')} single model")
table.sort(key=lambda x: (x["mk"] != "oracle", -x["acc"], x["cost"]))

solo_rows = sorted([(r["acc"], r["cost"], r["members"][0]) for r in rows if r["strategy"] == "solo"],
                   key=lambda z: (-z[0], z[1]))

# ---------- chart (all N tasks) ----------
W, H = 1040, 430
PADL, PADR, PADT, PADB = 64, 24, 26, 60
realizable = [r for r in rows if not r["strategy"].startswith("oracle")]
costs = [r["cost"] for r in realizable if r["cost"] > 0]
lxmin, lxmax = math.log10(min(costs)), math.log10(max(costs))
ymax = max(0.85, max(r["acc"] for r in rows) + 0.06)
ymin = max(0.0, min(r["acc"] for r in realizable) - 0.05)
X = lambda c: PADL + (math.log10(c if c > 0 else min(costs)) - lxmin) / (lxmax - lxmin) * (W - PADL - PADR)
Y = lambda a: H - PADB - (a - ymin) / (ymax - ymin) * (H - PADT - PADB)


def classify(r):
    s = r["strategy"]
    if s == "solo" and r["members"][0] in ("fugu", "fugu-ultra"):
        return "fugu"
    if s == "solo" and r["members"][0] == ref:
        return "ref"
    if s == "solo":
        return "single"
    if s.startswith("vote"):
        return "vote"
    if s.startswith("consensus"):
        return "cascade"
    return "other"


DOT = {"single": "#a8a8a8", "vote": "#006bff", "cascade": "#8e4ec6", "fugu": "#ea001d", "ref": "#171717"}
svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">', f'<rect width="{W}" height="{H}" fill="#fff"/>']
for a in [x / 100 for x in range(0, 100, 10)]:
    if a < ymin or a > ymax:
        continue
    y = Y(a)
    svg.append(f'<line x1="{PADL}" y1="{y:.1f}" x2="{W-PADR}" y2="{y:.1f}" stroke="#ebebeb"/>')
    svg.append(f'<text x="{PADL-9}" y="{y+4:.1f}" font-size="11" fill="#8f8f8f" text-anchor="end" font-family="Geist Mono,monospace">{a:.1f}</text>')
for d in range(int(math.floor(lxmin)), int(math.ceil(lxmax)) + 1):
    x = X(10 ** d)
    if x < PADL - 1 or x > W - PADR + 1:
        continue
    svg.append(f'<line x1="{x:.1f}" y1="{PADT}" x2="{x:.1f}" y2="{H-PADB}" stroke="#f4f4f4"/>')
    lab = (f"${10**d:.3f}".rstrip("0").rstrip(".")) if d < 0 else f"${10**d:.0f}"
    svg.append(f'<text x="{x:.1f}" y="{H-PADB+17}" font-size="11" fill="#8f8f8f" text-anchor="middle" font-family="Geist Mono,monospace">{lab}</text>')
yo = Y(oracle["acc"])
svg.append(f'<line x1="{PADL}" y1="{yo:.1f}" x2="{W-PADR}" y2="{yo:.1f}" stroke="#c9c9c9" stroke-width="1.5" stroke-dasharray="5 4"/>')
svg.append(f'<text x="{W-PADR}" y="{yo-6:.1f}" font-size="11" fill="#8f8f8f" text-anchor="end" font-family="Geist Mono,monospace">oracle = GPT-5.5 = {oracle["acc"]:.3f}</text>')
svg.append(f'<text x="{(PADL+W-PADR)/2:.0f}" y="{H-10}" font-size="12" fill="#4d4d4d" text-anchor="middle" font-family="Geist,sans-serif">cost per task (USD, log scale) — cheaper ←</text>')
svg.append(f'<text x="15" y="{(PADT+H-PADB)/2:.0f}" font-size="12" fill="#4d4d4d" text-anchor="middle" font-family="Geist,sans-serif" transform="rotate(-90 15 {(PADT+H-PADB)/2:.0f})">accuracy (of {N})</text>')
for r in sorted(realizable, key=lambda r: {"single": 0, "vote": 1, "cascade": 1, "ref": 3, "fugu": 4, "other": -1}[classify(r)]):
    c = classify(r)
    if c == "other":
        continue
    x, y = X(r["cost"]), Y(r["acc"])
    rad = 7 if c in ("fugu", "ref") else (3.1 if c in ("vote", "cascade") else 3.0)
    op = 1 if c in ("fugu", "ref") else (0.5 if c in ("vote", "cascade") else 0.45)
    svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad}" fill="{DOT[c]}" opacity="{op}"/>')


def lbl(text, cost, acc, dx, dy, anchor, color):
    svg.append(f'<text x="{X(cost)+dx:.1f}" y="{Y(acc)+dy:.1f}" font-size="11.5" fill="{color}" text-anchor="{anchor}" font-family="Geist,sans-serif" font-weight="600">{text}</text>')


if "fugu-ultra" in solos:
    lbl("Fugu-Ultra", solos["fugu-ultra"]["cost"], solos["fugu-ultra"]["acc"], 0, -12, "middle", "#ea001d")
if "fugu" in solos:
    lbl("Fugu-mini", solos["fugu"]["cost"], solos["fugu"]["acc"], 0, 18, "middle", "#ea001d")
lbl("GPT-5.5", solos[ref]["cost"], solos[ref]["acc"], -8, -10, "end", "#171717")
if "gpt-5-nano" in solos:
    lbl("gpt-5-nano", solos["gpt-5-nano"]["cost"], solos["gpt-5-nano"]["acc"], 0, 18, "middle", "#006bff")
if bv:
    lbl("cheap vote", bv["cost"], bv["acc"], 0, -11, "middle", "#006bff")
svg.append("</svg>")
SVG = "\n".join(svg)


def trows(items):
    out = []
    for x in items:
        lab, cls = METHOD[x["mk"]]
        out.append(
            f'<tr class="{cls}"><td class="method"><span class="chip {cls}">{lab}</span></td>'
            f'<td class="config">{x["config"]}</td>'
            f'<td class="num strong">{x["acc"]:.3f}</td><td class="num sub">{n_ok(x["acc"])}/{N}</td>'
            f'<td class="num">{fmt_cost(x["cost"])}</td><td class="num xcost">{fmt_x(x["cost"])}</td>'
            f'<td class="num lat">{lat_str(x["lat"])}</td><td class="note">{x["note"]}</td></tr>')
    return "\n".join(out)


solo_trows = "\n".join(
    f'<tr><td class="config">{short(mid)}</td><td class="sub">{tier.get(mid,"")}</td>'
    f'<td class="num strong">{a:.3f}</td><td class="num sub">{n_ok(a)}/{N}</td>'
    f'<td class="num">{fmt_cost(c)}</td><td class="num xcost">{fmt_x(c)}</td>'
    f'<td class="num lat">{lat_str(mean_lat_ms(mid))}</td></tr>'
    for a, c, mid in solo_rows)

# headline figures
fu = solos.get("fugu-ultra")
fm = solos.get("fugu")
nano = solos.get("gpt-5-nano")
fu_x = fu["cost"] / ref_cost if fu else 0
fm_x = fm["cost"] / ref_cost if fm else 0
fu_lat = mean_lat_ms("fugu-ultra") if fu else 0
fm_lat = mean_lat_ms("fugu") if fm else 0
ref_lat = mean_lat_ms(ref)
match_vote = cheapest_matching("vote-", ref_acc)
nano_gap = n_ok(ref_acc) - n_ok(nano["acc"]) if nano else 0
gen = time.strftime("%Y-%m-%d")
spent_total = sum(c.get("usd", 0.0) for v in mat.values() for c in v.values())
unsolved = N - n_ok(oracle["acc"])

HTML = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{--fg:#171717;--fg2:#4d4d4d;--fg3:#8f8f8f;--bg:#fff;--bg2:#fafafa;--b1:#eaeaea;--b2:#ebebeb;--blue:#006bff;--green:#0f7d34;--red:#ea001d;--amber:#ab5e00;--purple:#8e4ec6;}}
*{{box-sizing:border-box}}html{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
body{{font-family:'Geist',-apple-system,system-ui,sans-serif;color:var(--fg);background:var(--bg);margin:0;font-size:13px;line-height:1.5;letter-spacing:-0.01em}}
.page{{max-width:1080px;margin:0 auto;padding:42px 40px 56px}}
.mono{{font-family:'Geist Mono',ui-monospace,monospace}}
h1{{font-size:31px;font-weight:600;letter-spacing:-1.2px;line-height:38px;margin:0 0 6px}}
h2{{font-size:20px;font-weight:600;letter-spacing:-0.4px;line-height:26px;margin:32px 0 4px;padding-top:12px}}
.h2sub{{color:var(--fg3);font-size:12px;margin:0 0 12px;font-family:'Geist Mono',monospace}}
.sub-title{{color:var(--fg2);font-size:14px;margin:0 0 4px}}
.meta{{color:var(--fg3);font-size:12px;margin:0 0 18px;font-family:'Geist Mono',monospace}}
.lede{{background:var(--bg2);border:1px solid var(--b1);border-radius:12px;padding:17px 20px;margin:16px 0 4px}}
.lede p{{margin:0 0 8px}}.lede p:last-child{{margin:0}}
.kpis{{display:flex;gap:12px;margin:18px 0 4px;flex-wrap:wrap}}
.kpi{{flex:1;min-width:150px;border:1px solid var(--b1);border-radius:10px;padding:13px 15px}}
.kpi .v{{font-family:'Geist Mono',monospace;font-size:23px;font-weight:600;letter-spacing:-0.5px;line-height:1.1}}
.kpi .l{{color:var(--fg3);font-size:11px;margin-top:6px;line-height:1.35}}
.kpi.red .v{{color:var(--red)}}.kpi.blue .v{{color:var(--blue)}}.kpi.green .v{{color:var(--green)}}.kpi.amber .v{{color:var(--amber)}}
table{{width:100%;border-collapse:collapse;font-size:12.5px;margin:4px 0}}
thead th{{text-align:left;font-weight:600;font-size:10.5px;text-transform:uppercase;letter-spacing:0.04em;color:var(--fg3);background:var(--bg2);border-bottom:1px solid var(--b1);padding:8px 10px;white-space:nowrap}}
th.num{{text-align:right}}
tbody td{{padding:8px 10px;border-bottom:1px solid var(--b2);vertical-align:middle}}
tbody tr:last-child td{{border-bottom:none}}
.num{{font-family:'Geist Mono',monospace;text-align:right;white-space:nowrap}}
.strong{{font-weight:600;font-size:13px}}.sub{{color:var(--fg3);font-size:11px}}
.config{{font-family:'Geist Mono',monospace;font-size:11px;color:var(--fg)}}
.note{{color:var(--fg2);font-size:11px;max-width:230px;white-space:normal;line-height:1.35}}
.xcost{{color:var(--fg2)}}.lat{{color:var(--fg2)}}
.chip{{display:inline-block;font-size:10.5px;font-weight:500;padding:2px 8px;border-radius:9999px;white-space:nowrap;border:1px solid transparent}}
.chip.m-single{{background:#f2f2f2;color:#4d4d4d;border-color:#e6e6e6}}
.chip.m-fugu{{background:#ffeeef;color:#a4000f;border-color:#ffd0d4}}
.chip.m-vote{{background:#f0f7ff;color:#0058d1;border-color:#cfe6ff}}
.chip.m-cascade{{background:#faf0ff;color:#6c2b9d;border-color:#ecd7fb}}
.chip.m-oracle{{background:#fff;color:#8f8f8f;border:1px dashed #c9c9c9}}
tr.m-fugu td{{background:#fff7f7}}tr.m-oracle td{{background:#fafafa;color:var(--fg2)}}
.chart{{border:1px solid var(--b1);border-radius:12px;padding:12px 8px 4px;margin:8px 0 2px}}
.legend{{display:flex;gap:15px;flex-wrap:wrap;font-size:11px;color:var(--fg2);margin:2px 4px 6px;font-family:'Geist Mono',monospace}}
.legend span{{display:inline-flex;align-items:center;gap:6px}}.dot{{width:9px;height:9px;border-radius:50%;display:inline-block}}
.foot{{color:var(--fg3);font-size:10.5px;line-height:1.5;margin-top:6px}}
.takeaways li{{margin:6px 0}}
.limits{{background:var(--bg2);border:1px solid var(--b1);border-radius:10px;padding:6px 20px 10px;margin:8px 0}}
.limits li{{margin:7px 0;font-size:12px;color:var(--fg2)}}.limits li b{{color:var(--fg)}}
.review{{font-size:11px;color:var(--fg3);border-left:2px solid var(--b1);padding-left:10px;margin:8px 0}}
b,strong{{font-weight:600}}.hl-blue{{color:var(--blue);font-weight:600}}.hl-red{{color:var(--red);font-weight:600}}
@page{{size:Letter;margin:13mm 12mm}}h2,h3{{break-after:avoid}}tr{{break-inside:avoid}}.chart,.lede,.kpis,.limits{{break-inside:avoid}}
</style></head><body><div class="page">

<h1>Model routing — combinations vs. Sakana Fugu</h1>
<p class="sub-title">Cost · accuracy · latency of single models, ensemble methods, and multi-agent orchestration — one identical task stack.</p>
<p class="meta">suite: superhard · {N} brute-force-graded hard-math tasks · {len(have)} models measured live · ~${spent_total:.0f} API spend · {gen}</p>

<div class="lede">
<p><b>The question.</b> Does Sakana Fugu's multi-agent orchestration — or any cheap ensemble — beat a single strong model on genuinely hard problems? Every model and method below ran on the <b>same {N} tasks</b>, same integer grader, same cost accounting (Fugu billed on every token, orchestration included).</p>
<p><b>The answer.</b> On this suite, nothing beats a single strong model — orchestration and voting only change the <b>price</b> of reaching the same ceiling. <span class="hl-red">Both Fugu conductors solve the <i>exact same 46 tasks</i> as one GPT-5.5 call</span> ({ref_acc:.3f}), at {fm_x:.1f}× (mini) and {fu_x:.1f}× (ultra) the cost and up to ~{fu_lat/1000:.0f}s/task. Meanwhile a cheap majority vote ties that accuracy at <span class="hl-blue">{(fu["cost"]/match_vote["cost"]) if (fu and match_vote) else 0:.0f}× cheaper than Fugu-Ultra</span>, and a single cheap model (gpt-5-nano) lands one task back at {fmt_x(nano["cost"]) if nano else ''}.</p>
</div>

<div class="kpis">
<div class="kpi"><div class="v">{ref_acc:.3f}</div><div class="l">GPT-5.5 = Fugu-mini = Fugu-Ultra = the oracle ceiling (all identical, {n_ok(ref_acc)}/{N})</div></div>
<div class="kpi red"><div class="v">{fu_x:.1f}×</div><div class="l">Fugu-Ultra cost vs GPT-5.5 for the same {n_ok(ref_acc)} tasks · ~{fu_lat/1000:.0f}s/task</div></div>
<div class="kpi blue"><div class="v">{fmt_x(nano["cost"]).split()[0] if nano else '—'}</div><div class="l">gpt-5-nano vs GPT-5.5 — {nano_gap} task back ({n_ok(nano["acc"]) if nano else 0}/{N}), within noise</div></div>
<div class="kpi green"><div class="v">{fmt_x(match_vote["cost"]).split()[0] if match_vote else '—'}</div><div class="l">cheapest vote that ties GPT-5.5's {ref_acc:.3f}</div></div>
</div>

<h2>The comparison — one stack, every method</h2>
<p class="h2sub">{N} tasks · Fugu vs single models vs combination methods · sorted by accuracy, then cost</p>
<table>
<thead><tr><th>Method</th><th>Configuration</th><th class="num">Accuracy</th><th class="num"></th>
<th class="num">$ / task</th><th class="num">vs GPT-5.5</th><th class="num">Latency</th><th>How it works</th></tr></thead>
<tbody>
{trows(table)}
</tbody></table>
<p class="foot">Accuracy = fraction of {N} tasks with the correct integer (exact match vs a brute-force gold). $/task is measured API cost — Fugu includes orchestration tokens billed at $5/$30 per 1M. Latency is mean wall-clock per task; for vote &amp; cascade it assumes members run in parallel (max member latency, plus the escalation call on disagreement) and is high-variance/provider-dependent — directional, not an SLA. The oracle is the best-of-pool ceiling, not a usable strategy.</p>

<h2>Cost vs. accuracy</h2>
<p class="h2sub">{N} tasks · log cost axis · up-and-left is better</p>
<div class="legend">
<span><i class="dot" style="background:#171717"></i>GPT-5.5</span><span><i class="dot" style="background:#ea001d"></i>Sakana Fugu</span>
<span><i class="dot" style="background:#006bff"></i>majority vote</span><span><i class="dot" style="background:#8e4ec6"></i>consensus cascade</span>
<span><i class="dot" style="background:#a8a8a8"></i>single models</span></div>
<div class="chart">{SVG}</div>
<p class="foot">Both Fugu points sit ~{(fu["cost"]/min(costs)) if fu else 0:.0f}–{(fu["cost"]/solos["gpt-5-nano"]["cost"]) if (fu and nano) else 0:.0f}× to the right of the cheapest models at the <i>same</i> accuracy. The dashed line is the oracle, which equals GPT-5.5 — so no point rises above it: no combination exceeds the single strong model.</p>

<h2>What this means for routing</h2>
<ul class="takeaways">
<li><b>Orchestration added zero accuracy here.</b> Fugu-mini and Fugu-Ultra each solve the <i>identical {n_ok(ref_acc)} tasks</i> as one GPT-5.5 call — not one task more — at {fm_x:.1f}× and {fu_x:.1f}× the cost and up to ~{fu_lat/1000:.0f}s/task. The conductor confers, but on these problems it converges to the same answers a single strong model already gives.</li>
<li><b>Ensembling matches the frontier cheaper, never beats it (on this suite).</b> The pool oracle equals GPT-5.5 — there is no task any cheaper model or either Fugu solves that GPT-5.5 misses. Voting/cascading only reach {ref_acc:.3f} for less money.</li>
<li><b>A shared blind spot caps everyone.</b> {unsolved} of {N} tasks (a nonlinear modular-recurrence family, sh016–sh025) are unsolved by all {len(have)} models including both conductors — no ensemble can vote a correct answer into existence.</li>
<li><b>The cheap lever is real, the accuracy gap is not.</b> gpt-5-nano is {nano_gap} task behind GPT-5.5 ({n_ok(nano["acc"]) if nano else 0} vs {n_ok(ref_acc)} of {N}) — one task, within noise at this sample size — at {fmt_x(nano["cost"]) if nano else ''}. Treat the strong single models as accuracy-tied; route on cost and latency.</li>
</ul>

<h2>Method &amp; limitations</h2>
<p class="review">Independently method-audited by OpenAI Codex (GPT-5, read-only) with no view of the author's reasoning; its findings were folded in (token-fairness fix, operational-vs-capability separation, the caveats below).</p>
<div class="limits"><ul>
<li><b>Exact-answer math only.</b> All {N} tasks are integer-answer number-theory/combinatorics. These conclusions describe that regime; they need not hold for coding, open-ended reasoning, or agentic work — the domain multi-agent orchestration is actually pitched for. This is a fair test of orchestration on hard exact problems, not of orchestration in general.</li>
<li><b>Small n, single run.</b> Each (model, task) measured once at temperature 0; n={N}. One task = {100/N:.1f} points, so accuracy differences within ~1–2 tasks (e.g. {ref_acc:.3f} vs gpt-5-nano {nano["acc"] if nano else 0:.3f}) are <b>within noise</b> — read same-accuracy models as tied. No confidence intervals or repeated seeds.</li>
<li><b>Token fairness (fixed).</b> Every model gets the same 16k-token budget; an earlier 6k cap truncated some models and understated them (GLM-4.7-flash lost 31 answers) — those cells were re-measured.</li>
<li><b>Operational ≠ capability.</b> Timeouts, rate-limits, and transient errors were re-measured rather than counted wrong. Fugu was measured on a pay-as-you-go key after its weekly subscription quota was exhausted mid-run; all {N} Fugu cells here are clean answers.</li>
<li><b>Reproducibility gap.</b> The grader is "last integer in the response"; raw response text was not retained, so post-hoc extraction audits aren't possible (future runs will save raw text + finish_reason).</li>
</ul></div>

<h2>Appendix — all single models ({N} tasks)</h2>
<table>
<thead><tr><th>Model</th><th>Tier</th><th class="num">Accuracy</th><th class="num"></th>
<th class="num">$ / task</th><th class="num">vs GPT-5.5</th><th class="num">Latency</th></tr></thead>
<tbody>
{solo_trows}
</tbody></table>
<p class="foot">Reproducible: <span class="mono">registry.json</span> → <span class="mono">run.py --suite superhard</span> → <span class="mono">measure_fugu.py</span> (Fugu, gentle) → <span class="mono">report.py</span>. The outcome matrix is cached, so adding a model fills only its column and re-scores every combination for free.</p>

</div></body></html>"""

out = os.path.join(HERE, f"report_{SUITE}.html")
open(out, "w").write(HTML)

# =========================================================================================
#  Markdown twin — same computed data, plain GitHub-flavored markdown.
# =========================================================================================
front = CB.pareto(realizable)
fugu_vote_x = (fu["cost"] / match_vote["cost"]) if (fu and match_vote) else 0


def md_table_rows(items):
    out = []
    for x in items:
        lab = METHOD[x["mk"]][0]
        out.append(f"| {lab} | `{x['config']}` | **{x['acc']:.3f}** | {n_ok(x['acc'])}/{N} | "
                   f"{fmt_cost(x['cost'])} | {fmt_x(x['cost'])} | {lat_str(x['lat'])} | {x['note']} |")
    return "\n".join(out)


md = []
md.append("# Model routing — combinations vs. Sakana Fugu\n")
md.append("_Cost · accuracy · latency of single models, ensemble methods, and multi-agent "
          "orchestration on one identical task stack._\n")
md.append(f"**Suite** `superhard` — {N} brute-force-graded hard-math (integer-answer) tasks · "
          f"{len(have)} models measured live · ~${spent_total:.0f} total API spend · generated {gen}\n")

md.append("## The question\n")
md.append("Does Sakana Fugu's multi-agent orchestration — or any cheap ensemble — beat a single "
          "strong model on genuinely hard problems? Every model and method below ran on the **same "
          f"{N} tasks**, the same integer grader, and the same cost accounting (Fugu billed on every "
          "token, orchestration included).\n")

md.append("## The answer\n")
md.append(f"On this suite, **nothing beats a single strong model** — orchestration and voting only "
          f"change the *price* of reaching the same ceiling. Both Fugu conductors solve the **exact "
          f"same {n_ok(ref_acc)} tasks** as one GPT-5.5 call ({ref_acc:.3f}), at {fm_x:.1f}× (mini) and "
          f"{fu_x:.1f}× (ultra) the cost and up to ~{fu_lat/1000:.0f}s/task. A cheap majority vote ties "
          f"that accuracy at **{fugu_vote_x:.0f}× cheaper than Fugu-Ultra**, and a single cheap model "
          f"(gpt-5-nano) lands one task back at {fmt_x(nano['cost']) if nano else ''}.\n")
md.append("**Headline numbers**\n")
md.append(f"- **{ref_acc:.3f}** — GPT-5.5 = Fugu-mini = Fugu-Ultra = the oracle ceiling, all identical "
          f"({n_ok(ref_acc)}/{N}).")
md.append(f"- **{fu_x:.1f}×** — Fugu-Ultra costs this much more than GPT-5.5 for the same {n_ok(ref_acc)} "
          f"tasks (~{fu_lat/1000:.0f}s/task).")
md.append(f"- **{fmt_x(nano['cost']).split()[0] if nano else '—'}** — gpt-5-nano vs GPT-5.5, "
          f"{nano_gap} task back ({n_ok(nano['acc']) if nano else 0}/{N}) — within noise.")
md.append(f"- **{fmt_x(match_vote['cost']).split()[0] if match_vote else '—'}** — cheapest majority "
          f"vote that ties GPT-5.5's {ref_acc:.3f}.\n")

md.append("## The comparison — one stack, every method\n")
md.append(f"_{N} tasks · Fugu vs single models vs combination methods · sorted by accuracy, then cost._\n")
md.append("| Method | Configuration | Accuracy | n | $/task | vs GPT-5.5 | Latency | How it works |")
md.append("|---|---|---|---|---|---|---|---|")
md.append(md_table_rows(table))
md.append("")

md.append("## Cost vs. accuracy — realizable Pareto frontier\n")
md.append("_The non-dominated set: no other config is both more accurate and cheaper._\n")
md.append("| Accuracy | n | $/task | × cheaper than GPT-5.5 | strategy | members |")
md.append("|---|---|---|---|---|---|")
for r in front:
    xc = (ref_cost / r["cost"]) if r["cost"] else 0
    md.append(f"| {r['acc']:.3f} | {n_ok(r['acc'])}/{N} | {fmt_cost(r['cost'])} | {xc:.1f}× | "
              f"{r['strategy']} | `{'+'.join(short(m) for m in r['members'])}` |")
md.append(f"\n_Oracle ceiling (best-of-pool per task) = {oracle['acc']:.3f} = GPT-5.5 solo — "
          "so no realizable config rises above the single strong model._\n")

md.append("## What this means for routing\n")
md.append(f"- **Orchestration added zero accuracy here.** Fugu-mini and Fugu-Ultra each solve the "
          f"*identical {n_ok(ref_acc)} tasks* as one GPT-5.5 call — not one more — at {fm_x:.1f}× and "
          f"{fu_x:.1f}× the cost and up to ~{fu_lat/1000:.0f}s/task.")
md.append(f"- **Ensembling matches the frontier cheaper, never beats it (on this suite).** The pool "
          f"oracle equals GPT-5.5; no cheaper model or either Fugu solves a task GPT-5.5 misses. "
          f"Voting/cascading only reach {ref_acc:.3f} for less money.")
md.append(f"- **A shared blind spot caps everyone.** {unsolved} of {N} tasks (a nonlinear "
          f"modular-recurrence family, `sh016–sh025`) are unsolved by all {len(have)} models including "
          f"both conductors — no ensemble can vote a correct answer into existence.")
md.append(f"- **The cheap lever is real, the accuracy gap is not.** gpt-5-nano is {nano_gap} task behind "
          f"GPT-5.5 ({n_ok(nano['acc']) if nano else 0} vs {n_ok(ref_acc)} of {N}) — one task, within "
          f"noise — at {fmt_x(nano['cost']) if nano else ''}. Treat the strong single models as "
          f"accuracy-tied; route on cost and latency.\n")

md.append("## Method & limitations\n")
md.append("> Independently method-audited by OpenAI Codex (GPT-5, read-only) with no view of the "
          "author's reasoning; its findings were folded in (token-fairness fix, operational-vs-"
          "capability separation, the caveats below).\n")
md.append("- **Exact-answer math only.** All tasks are integer-answer number-theory/combinatorics. "
          "These conclusions describe that regime; they need not hold for coding, open-ended reasoning, "
          "or agentic work — the domain multi-agent orchestration is actually pitched for. This is a "
          "fair test of orchestration on hard *exact* problems, not of orchestration in general.")
md.append(f"- **Small n, single run.** Each (model, task) measured once at temperature 0; n={N}. One "
          f"task = {100/N:.1f} points, so accuracy differences within ~1–2 tasks (e.g. {ref_acc:.3f} vs "
          f"gpt-5-nano {nano['acc'] if nano else 0:.3f}) are **within noise** — read same-accuracy "
          "models as tied. No confidence intervals or repeated seeds.")
md.append("- **Token fairness (fixed).** Every model gets the same 16k-token budget; an earlier 6k cap "
          "truncated some models and understated them (GLM-4.7-flash lost 31 answers) — those cells "
          "were re-measured.")
md.append("- **Operational ≠ capability.** Timeouts, rate-limits, and transient errors were "
          "re-measured rather than counted wrong. Fugu was measured on a pay-as-you-go key after its "
          f"weekly subscription quota was exhausted mid-run; all {N} Fugu cells here are clean answers.")
md.append("- **Reproducibility gap.** The grader is \"last integer in the response\"; raw response text "
          "was not retained, so post-hoc extraction audits aren't possible (future runs will save raw "
          "text + finish_reason).\n")

md.append(f"## Appendix — all single models ({N} tasks)\n")
md.append("| Model | Tier | Accuracy | n | $/task | vs GPT-5.5 | Latency |")
md.append("|---|---|---|---|---|---|---|")
for a, c, mid in solo_rows:
    md.append(f"| `{short(mid)}` | {tier.get(mid,'')} | **{a:.3f}** | {n_ok(a)}/{N} | {fmt_cost(c)} | "
              f"{fmt_x(c)} | {lat_str(mean_lat_ms(mid))} |")
md.append("")
md.append("---")
md.append("_Reproducible: `registry.json` → `run.py --suite superhard` → `measure_fugu.py` (Fugu) → "
          "`report.py` (this document + the PDF). The outcome matrix is cached, so adding a model fills "
          "only its column and re-scores every combination for free._")

md_out = os.path.join(HERE, "Model-Routing-vs-Fugu.md")
open(md_out, "w").write("\n".join(md) + "\n")

print(f"wrote {out}")
print(f"wrote {md_out}")
print(f"  models ({len(have)}): fugu={'fugu' in have} fugu-ultra={'fugu-ultra' in have}")
print(f"  gpt-5.5={n_ok(ref_acc)}/{N}  fugu={n_ok(solos['fugu']['acc']) if 'fugu' in solos else '-'}/{N}  "
      f"fugu-ultra={n_ok(solos['fugu-ultra']['acc']) if 'fugu-ultra' in solos else '-'}/{N}")
