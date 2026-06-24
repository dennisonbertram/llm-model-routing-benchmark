"""Aggregate metrics + Pareto-frontier tabulation for routing runs."""


class RunResult:
    """Per-item outcomes for one router over one suite."""

    def __init__(self, name):
        self.name = name
        self.items = []  # each: {id, discipline, difficulty, correct, usd, latency_ms, models, decision}

    def add(self, item, correct, usd, latency_ms, models, decision=None):
        self.items.append({
            "id": item["id"], "discipline": item["discipline"], "difficulty": item.get("difficulty"),
            "correct": bool(correct), "usd": float(usd), "latency_ms": int(latency_ms),
            "models": models, "decision": decision,
        })

    def n(self):
        return len(self.items)

    def accuracy(self):
        return sum(i["correct"] for i in self.items) / max(1, self.n())

    def total_usd(self):
        return sum(i["usd"] for i in self.items)

    def mean_latency(self):
        return sum(i["latency_ms"] for i in self.items) / max(1, self.n())

    def usd_per_correct(self):
        c = sum(i["correct"] for i in self.items)
        return self.total_usd() / c if c else float("inf")

    def pct_cheap(self, cheap_models):
        cm = set(cheap_models)
        routed_cheap = sum(1 for i in self.items if set(i["models"]) & cm and not (set(i["models"]) - cm))
        return routed_cheap / max(1, self.n())

    def by_difficulty(self):
        out = {}
        for i in self.items:
            d = i["difficulty"] or "?"
            out.setdefault(d, [0, 0])
            out[d][1] += 1
            out[d][0] += i["correct"]
        return {k: (v[0], v[1], v[0] / v[1]) for k, v in out.items()}

    def row(self):
        return {
            "router": self.name, "n": self.n(), "accuracy": round(self.accuracy(), 4),
            "total_usd": round(self.total_usd(), 6), "usd_per_correct": round(self.usd_per_correct(), 6),
            "mean_latency_ms": int(self.mean_latency()),
        }


def pareto_front(rows, acc_key="accuracy", cost_key="total_usd"):
    """Return the subset of rows on the cost-quality Pareto frontier (higher acc, lower cost).
    A row is dominated if another has >= accuracy AND <= cost with at least one strict."""
    front = []
    for r in rows:
        dominated = False
        for s in rows:
            if s is r:
                continue
            if s[acc_key] >= r[acc_key] and s[cost_key] <= r[cost_key] and (
                s[acc_key] > r[acc_key] or s[cost_key] < r[cost_key]):
                dominated = True
                break
        if not dominated:
            front.append(r)
    return front


def format_table(rows, cols=None):
    cols = cols or ["router", "n", "accuracy", "total_usd", "usd_per_correct", "mean_latency_ms"]
    head = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = []
    for r in rows:
        body.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return "\n".join([head, sep] + body)
