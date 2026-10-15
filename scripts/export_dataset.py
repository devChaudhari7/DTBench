"""Export the DTBench dataset (specs, ground-truth tables, reference code, probes) to data/DTBench/."""
import csv
import inspect
import importlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dtbench.probes import gt_probes          # noqa: E402
from dtbench.specs import SPECS               # noqa: E402

OUT = ROOT / "data" / "DTBench"

README = """# DTBench: business rules with ground-truth decision tables

DTBench is a small benchmark for evaluating how well large language models (LLMs) turn
natural-language business rules into **decision tables** and **decision-table test cases**.
It accompanies the STQA term paper *LLM-Based Generation and Validation of Decision Table Test Cases*.

Each of the 12 specifications contains:

| Field | Meaning |
|---|---|
| `rules_text` | the business rules exactly as given to the LLM |
| `inputs`, `output`, `constraint` | the data dictionary (names, types, domains, allowed outputs) |
| `ground_truth_table` | a limited-entry decision table: conditions are boolean expressions over the inputs, rules map each condition to true/false/don't care and give the output |
| `infeasible_rules` | combinations of condition values that no valid input can reach (S01 only) |
| `reference_implementation` | an independently written Python function `decide(**inputs)` used as the test oracle |
| `probes` (separate file) | the evaluation inputs used to compare tables and test cases with the ground truth |

## Specifications

{table}

Totals: {n_specs} specifications, {n_rules} feasible ground-truth rules, {n_probes} evaluation probes.

## How the ground truth was built and checked

The ground-truth tables were derived manually following the decision-table procedure in
Jorgensen (2013, ch. 7): one rule per distinct case stated in the specification, with a
"don't care" entry only where the specification makes a condition irrelevant. Each table
was then checked automatically (`scripts/verify_benchmark.py`): on every evaluation probe
exactly one rule fires and its output equals the independent reference implementation,
every rule is reached by at least one probe, and no probe reaches an infeasible rule.

## Sources and licence

* S01, S02: classic textbook problems (Jorgensen 2013; Myers et al. 2011), rules re-worded.
* S04 to S09: descriptions from the GPT-DMN data set of Goossens, Vandevelde, Vanthienen and
  Vennekens, "GPT-3 for Decision Logic Modeling", RuleML+RR 2023 (CEUR-WS Vol. 3485),
  https://gitlab.com/EAVISE/sva/GPT-DMN . They are reproduced with attribution for research use;
  S07 originates from the DMCommunity challenge of January 2016 (J. Vanthienen). Changes are
  listed per specification in the `clarifications` field (S08 boundary wording; data dictionaries added).
* S03, S10, S11, S12: written for this benchmark. S11 is a simplified illustration, not an official
  NPCI rule set.

Content written for DTBench (rules S03, S10 to S12, all data dictionaries, ground-truth tables,
reference implementations and probes) is released under CC BY 4.0. The GPT-DMN descriptions remain
under the terms of their original authors.

## Files

```
dtbench_specs.json          all specifications in one file
specs/Sxx_<name>.json       one file per specification
dtbench_summary.csv         one row per specification
ground_truth_tables.md      the ground-truth tables in readable T/F/- form
reference/sxx_<name>.py     reference implementations
probes/Sxx.jsonl            evaluation probes with ground-truth rule and expected output
```
"""


def slug(s):
    return "".join(ch if ch.isalnum() else "_" for ch in s.lower()).strip("_").replace("__", "_")


def spec_record(spec):
    mod = importlib.import_module(f"dtbench.reference.{spec.reference}")
    return {
        "id": spec.id, "name": spec.name, "category": spec.category,
        "source": spec.source, "source_url": spec.source_url,
        "rules_text": spec.rules_text, "clarifications": spec.clarifications,
        "inputs": [{"name": v.name, "type": v.type, "min": v.lo, "max": v.hi,
                    "values": list(v.values) or None, "description": v.desc} for v in spec.inputs],
        "constraint": spec.constraint, "constraint_description": spec.constraint_desc or None,
        "output": {"name": spec.output_name, "type": spec.output_type,
                   "values": list(spec.output_values) or None},
        "ground_truth_table": {"conditions": spec.gt_table["conditions"], "rules": spec.gt_table["rules"]},
        "infeasible_rules": spec.gt_table.get("infeasible_rules", []),
        "n_feasible_rules": len(spec.feasible_gt_rules()),
        "tags": list(spec.tags),
        "reference_implementation": f"reference/{spec.reference}.py",
        "reference_source": inspect.getsource(mod),
    }


def matrix_md(spec):
    t = spec.gt_table
    rules = t["rules"]
    head = "| Condition | " + " | ".join(r["id"] for r in rules) + " |"
    sep = "|---|" + "---|" * len(rules)
    lines = [head, sep]
    for c in t["conditions"]:
        cells = []
        for r in rules:
            v = r["when"].get(c["id"])
            cells.append("T" if v is True else "F" if v is False else "-")
        lines.append(f"| {c['id']}: `{c['expr']}` | " + " | ".join(cells) + " |")
    lines.append("| **Output** | " + " | ".join(str(r["output"]) for r in rules) + " |")
    return "\n".join(lines)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "specs").mkdir(parents=True)
    (OUT / "reference").mkdir()
    (OUT / "probes").mkdir()
    records, rows, n_probes = [], [], 0
    md = ["# DTBench ground-truth decision tables\n",
          "T = condition true, F = false, - = don't care. Each column is one rule.\n"]
    from dtbench.table import DecisionTable
    for spec in SPECS:
        rec = spec_record(spec)
        records.append(rec)
        (OUT / "specs" / f"{spec.id}_{slug(spec.name)}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False))
        shutil.copy(ROOT / "dtbench" / "reference" / f"{spec.reference}.py", OUT / "reference")
        gt = DecisionTable(spec.gt_table, spec)
        probes = gt_probes(spec)
        n_probes += len(probes)
        with open(OUT / "probes" / f"{spec.id}.jsonl", "w") as f:
            for p in probes:
                _, out, ids = gt.decide(p)
                f.write(json.dumps({"inputs": p, "gt_rule": ids[0], "expected": out}) + "\n")
        rows.append({"id": spec.id, "name": spec.name, "category": spec.category, "inputs": len(spec.inputs),
                     "conditions": len(spec.gt_table["conditions"]), "rules": len(spec.feasible_gt_rules()),
                     "probes": len(probes), "tags": "; ".join(spec.tags), "source": spec.source,
                     "source_url": spec.source_url})
        md += [f"\n## {spec.id} {spec.name}\n", f"Source: {spec.source}\n",
               f"Output: `{spec.output_name}`\n", matrix_md(spec), ""]
        if spec.gt_table.get("infeasible_rules"):
            md.append("Infeasible combinations (not counted): " + "; ".join(
                ", ".join(f"{k}={'T' if v else 'F'}" for k, v in r["when"].items()) + f" ({r['note']})"
                for r in spec.gt_table["infeasible_rules"]) + "\n")
    (OUT / "dtbench_specs.json").write_text(json.dumps(records, indent=2, ensure_ascii=False))
    with open(OUT / "dtbench_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (OUT / "ground_truth_tables.md").write_text("\n".join(md))
    table = ["| ID | Name | Category | Inputs | Conditions | Rules | Probes |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        table.append(f"| {r['id']} | {r['name']} | {r['category']} | {r['inputs']} | {r['conditions']} | "
                     f"{r['rules']} | {r['probes']} |")
    (OUT / "README.md").write_text(README.format(table="\n".join(table), n_specs=len(rows),
                                                 n_rules=sum(r["rules"] for r in rows), n_probes=n_probes))
    print(f"exported {len(rows)} specs, {sum(r['rules'] for r in rows)} rules, {n_probes} probes to {OUT}")


if __name__ == "__main__":
    main()
