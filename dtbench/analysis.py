"""Compute all metrics from the cached LLM outputs.

    python -m dtbench.analysis            # reads results/raw, writes results/*.json|csv

Test suites:
  P0  test cases written directly by the LLM
  P1  derived mechanically (dtbench.derive) from the LLM's first decision table
  P2  derived mechanically from the table after ground-truth-free validation and repair
  REF derived with the same procedure from the ground-truth table (upper reference)
"""
import argparse
import csv
import json
import pathlib

from . import mutation
from .derive import derive_tests
from .probes import gt_probes
from .specs import SPECS
from .table import DecisionTable
from .test_eval import assess_tests
from .validator import gt_table_eval, structural_check

ROOT = pathlib.Path(__file__).resolve().parents[1]
STRATEGY_NAMES = {"P0": "Direct", "P1": "Table-first", "P2": "Table-first + validation", "REF": "Ground-truth table"}
MODEL_NAMES = {"qwen3-4b": "Qwen3-4B", "llama3.2-3b": "Llama-3.2-3B", "gemma3-4b": "Gemma-3-4B"}


class SpecContext:
    """Ground truth, evaluation probes and mutants for one spec (computed once)."""

    def __init__(self, spec):
        self.spec = spec
        self.gt = DecisionTable(spec.gt_table, spec)
        self.probes = gt_probes(spec)
        self.mutants = mutation.mark_equivalents(spec, mutation.generate(spec), self.probes)


def _load(path):
    return json.loads(path.read_text()) if path.exists() else None


def _llm_tests(rec):
    if not rec or not isinstance(rec.get("parsed"), dict):
        return []
    t = rec["parsed"].get("tests")
    return t if isinstance(t, list) else []


def _usage(recs):
    recs = [r for r in recs if r]
    return {"llm_calls": len(recs),
            "llm_seconds": round(sum(r.get("seconds") or 0 for r in recs), 1),
            "completion_tokens": sum((r.get("usage") or {}).get("completion_tokens") or 0 for r in recs),
            "prompt_tokens": sum((r.get("usage") or {}).get("prompt_tokens") or 0 for r in recs)}


def table_metrics(table_obj, ctx):
    """Metrics for one LLM table; returns (metrics, DecisionTable or None)."""
    if not isinstance(table_obj, dict):
        return {"table_parsed": False, "table_usable": False}, None
    dt = DecisionTable(table_obj, ctx.spec)
    out = {"table_parsed": True, "table_usable": dt.usable, "n_conditions": len(dt.conditions),
           "n_table_rules": len(dt.rules), "n_problems": len(dt.problems)}
    if not dt.usable:
        return out, None
    chk = structural_check(dt, ctx.spec)
    out.update({"sc_gap_combinations": chk["gap_combinations"],
                "sc_conflict_combinations": chk["conflict_combinations"],
                "sc_issues": chk["issue_count"],
                "sc_clean": chk["issue_count"] == 0})
    out.update(gt_table_eval(dt, ctx.spec, ctx.probes, ctx.gt))
    return out, dt


def evaluate_model(model, raw_dir, ctxs):
    rows = []
    for spec in SPECS:
        ctx = ctxs[spec.id]
        d = raw_dir / spec.id
        if not (d / "P2_summary.json").exists():
            continue
        p0 = _load(d / "P0_tests.json")
        p1 = _load(d / "P1_table.json")
        summ = _load(d / "P2_summary.json")
        repairs = [r for r in (_load(d / f"P2_repair{i}.json") for i in (1, 2)) if r]
        base = {"model": model, "spec": spec.id}

        m0 = assess_tests(_llm_tests(p0), spec, ctx.gt, ctx.mutants)
        rows.append({**base, "strategy": "P0", **m0, **_usage([p0]),
                     "json_ok": bool(p0 and isinstance(p0.get("parsed"), dict))})

        tm1, dt1 = table_metrics((p1 or {}).get("parsed"), ctx)
        m1 = assess_tests(derive_tests(dt1, spec) if dt1 else [], spec, ctx.gt, ctx.mutants)
        rows.append({**base, "strategy": "P1", **tm1, **m1, **_usage([p1]),
                     "json_ok": bool(p1 and isinstance(p1.get("parsed"), dict))})

        tm2, dt2 = table_metrics(summ.get("final_table"), ctx)
        m2 = assess_tests(derive_tests(dt2, spec) if dt2 else [], spec, ctx.gt, ctx.mutants)
        hist = summ.get("history", [])
        first = hist[0] if hist else {}
        rows.append({**base, "strategy": "P2", **tm2, **m2, **_usage([p1] + repairs),
                     "json_ok": isinstance(summ.get("final_table"), dict),
                     "repair_rounds": len(repairs), "table_changed": bool(summ.get("changed")),
                     "issues_reported_round1": len(first.get("issues", [])),
                     "sc_gaps_before": first.get("gap_combinations"),
                     "sc_conflicts_before": first.get("conflict_combinations")})
    return rows


def reference_rows(ctxs):
    rows = []
    for spec in SPECS:
        ctx = ctxs[spec.id]
        m = assess_tests(derive_tests(ctx.gt, spec), spec, ctx.gt, ctx.mutants)
        rows.append({"model": "ground-truth", "spec": spec.id, "strategy": "REF", **m})
    return rows


def benchmark_rows(ctxs):
    rows = []
    for s in SPECS:
        ctx = ctxs[s.id]
        live = [m for m in ctx.mutants if not m.equivalent]
        rows.append({"spec": s.id, "name": s.name, "category": s.category, "inputs": len(s.inputs),
                     "gt_conditions": len(s.gt_table["conditions"]), "gt_rules": len(s.feasible_gt_rules()),
                     "infeasible_rules": len(s.gt_table.get("infeasible_rules", [])),
                     "probes": len(ctx.probes), "mutants": len(ctx.mutants),
                     "equivalent_mutants": len(ctx.mutants) - len(live), "live_mutants": len(live),
                     "tags": "; ".join(s.tags)})
    return rows


def write_csv(path, rows):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (";".join(v) if isinstance(v, list) else v) for k, v in r.items()})


def run(raw=ROOT / "results" / "raw", out=ROOT / "results"):
    raw, out = pathlib.Path(raw), pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ctxs = {s.id: SpecContext(s) for s in SPECS}
    bench = benchmark_rows(ctxs)
    rows = reference_rows(ctxs)
    models = [m for m in MODEL_NAMES if (raw / m).is_dir()] + sorted(
        p.name for p in raw.iterdir() if p.is_dir() and p.name not in MODEL_NAMES) if raw.exists() else []
    for m in models:
        rows += evaluate_model(m, raw / m, ctxs)
    (out / "benchmark_summary.json").write_text(json.dumps(bench, indent=1))
    write_csv(out / "benchmark_summary.csv", bench)
    (out / "metrics_rows.json").write_text(json.dumps(rows, indent=1))
    write_csv(out / "metrics_rows.csv", rows)
    return rows, bench


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(ROOT / "results" / "raw"))
    ap.add_argument("--out", default=str(ROOT / "results"))
    a = ap.parse_args()
    rows, bench = run(a.raw, a.out)
    print(f"{len(rows)} metric rows; models: {sorted({r['model'] for r in rows})}")


if __name__ == "__main__":
    main()
