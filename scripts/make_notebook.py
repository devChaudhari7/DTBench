"""Create notebooks/DTBench_Experiment.ipynb (a runnable walkthrough of the whole pipeline)."""
import pathlib

import nbformat as nbf

ROOT = pathlib.Path(__file__).resolve().parents[1]

cells = []


def md(text):
    cells.append(nbf.v4.new_markdown_cell(text.strip()))


def code(text):
    cells.append(nbf.v4.new_code_cell(text.strip()))


md("""
# DTBench: LLM-based generation and validation of decision-table test cases

Runnable walkthrough of the experiment. It uses the model responses saved in `results/raw`, so no LLM is
needed. Run all cells from top to bottom (about one minute).

1. Benchmark: specifications, ground-truth tables, verification
2. One specification end to end (S07 vacation days)
3. Ground-truth-free validation and repair of a model's table
4. Full results, statistics and figures
5. Mutation analysis example
""")
code("""
import json, pathlib, sys, inspect
ROOT = pathlib.Path.cwd() if (pathlib.Path.cwd() / "dtbench").exists() else pathlib.Path.cwd().parent
sys.path.insert(0, str(ROOT))
import pandas as pd
from IPython.display import Image, display
from dtbench.specs import SPECS, SPEC_BY_ID
from dtbench.table import DecisionTable
from dtbench.probes import gt_probes
from dtbench.validator import structural_check, issues_text, gt_table_eval
from dtbench.derive import derive_tests
from dtbench.test_eval import assess_tests
from dtbench import mutation
pd.set_option("display.max_colwidth", 120)
print("repository:", ROOT)
""")
md("## 1. Benchmark")
code("""
pd.DataFrame([{"id": s.id, "name": s.name, "category": s.category, "inputs": len(s.inputs),
               "gt_conditions": len(s.gt_table["conditions"]), "gt_rules": len(s.feasible_gt_rules()),
               "tags": ", ".join(s.tags)} for s in SPECS])
""")
code("""
# Every ground-truth table must agree with its independent reference implementation on every probe
rows = []
for s in SPECS:
    gt = DecisionTable(s.gt_table, s)
    probes = gt_probes(s)
    mismatches = sum(1 for p in probes if gt.decide(p)[1] != s.reference_output(p))
    rows.append({"spec": s.id, "probes": len(probes), "mismatches": mismatches})
check = pd.DataFrame(rows)
print("total probes:", check.probes.sum(), "| total mismatches:", check.mismatches.sum())
check
""")
md("## 2. One specification end to end: S07 vacation days")
code("""
spec = SPEC_BY_ID["S07"]
print(spec.rules_text, "\\n")
print(spec.describe_inputs())
print(spec.describe_output())
""")
code("""
def show_table(table):
    m = table.matrix()
    cols = ["id", "condition"] + [r.id for r in table.rules]
    return pd.DataFrame(m, columns=cols)

gt = DecisionTable(spec.gt_table, spec)
show_table(gt)
""")
code("""
print(inspect.getsource(spec.reference_fn()))
""")
md("## 3. Ground-truth-free validation and repair of a model's table")
code("""
MODEL = "qwen3-4b"
raw = ROOT / "results" / "raw" / MODEL / spec.id
p1 = json.loads((raw / "P1_table.json").read_text())
print("prompt sent to the model:\\n")
print(p1["messages"][1]["content"])
""")
code("""
t1 = DecisionTable(p1["parsed"], spec)
show_table(t1)
""")
code("""
check = structural_check(t1, spec)
print("probes:", check["n_probes"], "| condition combinations:", check["n_combinations"],
      "| missing combinations:", check["gap_combinations"], "| conflicts:", check["conflict_combinations"])
for line in issues_text(t1, spec, check):
    print("-", line)
""")
code("""
summary = json.loads((raw / "P2_summary.json").read_text())
print("repair rounds:", sum(1 for i in (1, 2) if (raw / f"P2_repair{i}.json").exists()),
      "| table changed:", summary["changed"])
t2 = DecisionTable(summary["final_table"], spec)
c2 = structural_check(t2, spec)
print("after repair -> missing combinations:", c2["gap_combinations"], "| conflicts:", c2["conflict_combinations"])
show_table(t2)
""")
code("""
probes = gt_probes(spec)
mutants = mutation.mark_equivalents(spec, mutation.generate(spec), probes)
res = []
for name, table in (("P1 table", t1), ("P2 table", t2), ("ground truth", gt)):
    tests = derive_tests(table, spec)
    m = assess_tests(tests, spec, gt, mutants)
    e = gt_table_eval(table, spec, probes, gt)
    res.append({"table": name, "rules": len(table.rules), "table accuracy": round(e["probe_accuracy"], 3),
                "tests": m["n_tests"], "oracle accuracy": round(m["oracle_accuracy"], 3),
                "rule coverage": round(m["rule_coverage"], 3), "missed rules": ", ".join(m["missed_rules"]),
                "mutation score": round(m["mutation_score"], 3)})
pd.DataFrame(res)
""")
md("## 4. Full results")
code("""
import runpy
_ = runpy.run_path(str(ROOT / "scripts" / "make_results.py"), run_name="__main__")
""")
code("""
summary = pd.read_csv(ROOT / "results" / "summary.csv")
cols = ["model", "strategy", "tests_total", "validity", "oracle_accuracy", "rule_coverage_pooled",
        "missed_total", "mutation_score_pooled", "tables_clean", "table_accuracy"]
summary[[c for c in cols if c in summary.columns]].round(3)
""")
code("""
pd.DataFrame(json.loads((ROOT / "results" / "stats.json").read_text())).round(4)
""")
code("""
for f in ("architecture.png", "fig_coverage_mutation.png", "fig_heatmap_rule_coverage.png", "fig_validation_repair.png"):
    display(Image(filename=str(ROOT / "figures" / f), width=900))
""")
md("## 5. Mutation analysis example (S11 UPI transfer screening)")
code("""
s11 = SPEC_BY_ID["S11"]
p11 = gt_probes(s11)
m11 = mutation.mark_equivalents(s11, mutation.generate(s11), p11)
gt11 = DecisionTable(s11.gt_table, s11)
ref_tests = [(t["inputs"], s11.reference_output(t["inputs"])) for t in derive_tests(gt11, s11)]
killed = mutation.kills(s11, m11, ref_tests)
pd.DataFrame([{"mutant": m.id, "operator": m.op, "change": m.desc, "equivalent": m.equivalent,
               "killed by reference suite": m.id in killed} for m in m11])
""")

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
out = ROOT / "notebooks" / "DTBench_Experiment.ipynb"
out.parent.mkdir(exist_ok=True)
nbf.write(nb, out)
print("wrote", out)
