"""All-night model-combination benchmark — entry point.

  1. measure every enabled model in registry.json on the suite (resumable, parallel, budget-capped),
  2. evaluate solos + all k<=max-k votes + consensus-escalate + oracle OFFLINE,
  3. write a cost-accuracy leaderboard (Pareto frontier + full table) + results.json.

Run overnight:  set -a; . .agent-university/secrets.local.env; set +a
  nohup python3 run.py --suite superhard --budget 25 --max-k 4 --timeout 90 > bench/run.log 2>&1 &

Re-run anytime — measurement resumes from matrix_<suite>.json (already-measured pairs are free).
Add models to registry.json and re-run to extend; only the new pairs get measured.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import matrix as MX
import combos as CB
import suites as SU


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="superhard")
    ap.add_argument("--budget", type=float, default=25.0, help="USD cap on live measurement")
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--max-k", type=int, default=4, help="largest ensemble size to evaluate")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--limit", type=int, default=0, help="cap #tasks (0=all); use for a fast smoke test")
    args = ap.parse_args()

    reg = json.load(open(os.path.join(HERE, "registry.json")))["models"]
    models = [m["id"] for m in reg if m.get("enabled", True)]
    ref = next((m["id"] for m in reg if m.get("reference")), None)
    tasks = SU.load(args.suite)
    if args.limit:
        tasks = tasks[:args.limit]
    gold = {t["id"]: t["gold"] for t in tasks}
    mpath = os.path.join(HERE, f"matrix_{args.suite}.json")

    def log(*a):
        print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)

    log(f"=== BENCH: suite={args.suite} ({len(tasks)} tasks), {len(models)} models, "
        f"ref={ref}, budget=${args.budget}, max_k={args.max_k} ===")
    mat, spent = MX.measure_all(models, tasks, mpath, timeout=args.timeout, budget_usd=args.budget,
                                max_workers=args.workers, log=log)
    # only evaluate models we actually have full coverage for
    have = [m for m in models if all(t["id"] in mat.get(m, {}) for t in tasks)]
    log(f"measured full coverage for {len(have)}/{len(models)} models: {have}")

    rows = CB.evaluate_all(mat, have, tasks, gold, ref=ref, max_k=args.max_k)
    rows.sort(key=lambda r: (-r["acc"], r["cost"]))
    realizable = [r for r in rows if not r["strategy"].startswith("oracle")]
    front = CB.pareto(realizable)
    ref_row = next((r for r in rows if r["strategy"] == "solo" and r["members"] == [ref]), None)

    # ---- write leaderboard.md ----
    lines = [f"# Benchmark leaderboard — suite `{args.suite}` ({len(tasks)} tasks)",
             f"_measured {len(have)} models, spent ~${spent:.4f}, generated {time.strftime('%Y-%m-%d %H:%M')}_", ""]
    if ref_row:
        lines += [f"**Reference {ref}: acc={ref_row['acc']:.3f}, ${ref_row['cost']:.5f}/task**", ""]
    lines += ["## Realizable cost-accuracy Pareto frontier", "", "| acc | $/task | × cheaper than ref | strategy | members |",
              "|---|---|---|---|---|"]
    for r in front:
        xc = (ref_row["cost"] / r["cost"]) if (ref_row and r["cost"]) else 0
        lines.append(f"| {r['acc']:.3f} | {r['cost']:.5f} | {xc:.1f}× | {r['strategy']} | {'+'.join(m.split('/')[-1] for m in r['members'])} |")
    # cheapest config matching the reference accuracy
    if ref_row:
        match = [r for r in realizable if r["acc"] >= ref_row["acc"] - 1e-9]
        if match:
            ch = min(match, key=lambda r: r["cost"])
            lines += ["", f"**Cheapest config matching ref accuracy ({ref_row['acc']:.3f}):** "
                      f"{ch['strategy']} [{'+'.join(m.split('/')[-1] for m in ch['members'])}] = {ch['acc']:.3f} @ "
                      f"${ch['cost']:.5f}/task ({ref_row['cost']/ch['cost']:.1f}× cheaper)"]
        else:
            best = max(realizable, key=lambda r: r["acc"])
            lines += ["", f"**No config matched ref accuracy.** Best realizable: {best['strategy']} "
                      f"[{'+'.join(m.split('/')[-1] for m in best['members'])}] = {best['acc']:.3f} @ ${best['cost']:.5f}/task"]
    oracle_row = next((r for r in rows if r["strategy"].startswith("oracle")), None)
    if oracle_row:
        lines += ["", f"_oracle ceiling (pool): {oracle_row['acc']:.3f} @ ${oracle_row['cost']:.5f}/task (unrealizable)_"]
    lines += ["", "## Full table (top 60 by accuracy, then cost)", "",
              "| acc | $/task | strategy | members |", "|---|---|---|---|"]
    for r in rows[:60]:
        lines.append(f"| {r['acc']:.3f} | {r['cost']:.5f} | {r['strategy']} | {'+'.join(m.split('/')[-1] for m in r['members'])} |")
    open(os.path.join(HERE, f"leaderboard_{args.suite}.md"), "w").write("\n".join(lines) + "\n")
    json.dump({"suite": args.suite, "n_tasks": len(tasks), "spent": spent, "ref": ref,
               "measured": have, "rows": rows, "frontier": front},
              open(os.path.join(HERE, f"results_{args.suite}.json"), "w"), indent=1)
    log(f"wrote leaderboard_{args.suite}.md + results_{args.suite}.json ({len(rows)} configs evaluated)")
    # console summary
    print("\n=== TOP OF FRONTIER ===")
    for r in front[:8]:
        print(f"  {r['acc']:.3f}  ${r['cost']:.5f}/task  {r['strategy']:22} {'+'.join(m.split('/')[-1] for m in r['members'])}")


if __name__ == "__main__":
    main()
