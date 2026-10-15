"""Decision-table validation.

* ``structural_check`` - ground-truth-free check that a practitioner could run on
  any LLM-generated table: predicate-guided probing finds the realisable
  combinations of the table's own conditions and reports combinations matched by
  no rule (gaps = missed combinations) and by rules with different outputs
  (conflicts = inconsistency), plus malformed conditions, references and outputs.
* ``gt_table_eval`` - evaluation against the ground-truth table and reference
  implementation on the benchmark's evaluation probes.
"""
import collections

from .expr import parse_expr
from .probes import synthesize


def _fmt_inputs(spec, p):
    parts = []
    for v in spec.inputs:
        x = p[v.name]
        if isinstance(x, bool):
            x = "true" if x else "false"
        elif isinstance(x, str):
            x = f'"{x}"'
        elif isinstance(x, float):
            x = f"{x:g}"
        parts.append(f"{v.name}={x}")
    return ", ".join(parts)


def structural_check(table, spec, seed=7):
    trees = [c.tree for c in table.conditions.values()]
    if spec.constraint:
        trees.append(parse_expr(spec.constraint, spec.var_names))
    probes = synthesize(spec, trees, seed=seed, max_product=6000, n_relation=50, n_random=1200)
    groups = collections.OrderedDict()
    for p in probes:
        vec = table.condition_vector(p)
        groups.setdefault(vec, []).append(p)
    gaps, conflicts, errors, redundant = [], [], [], 0
    gap_probes = conflict_probes = 0
    for vec, pts in groups.items():
        if any(v is None for v in vec):
            errors.append((vec, pts[0]))
            continue
        fired = table.fired_from_vector(vec)
        if not fired:
            gaps.append((vec, pts[0], len(pts)))
            gap_probes += len(pts)
            continue
        outs = {table.rules[i].output for i in fired}
        if len(outs) > 1:
            conflicts.append((vec, pts[0], [table.rules[i].id for i in fired],
                              [table.rules[i].raw_output for i in fired], len(pts)))
            conflict_probes += len(pts)
        elif len(fired) > 1:
            redundant += 1
    n = max(len(probes), 1)
    return {
        "problems": table.problems,
        "n_probes": len(probes),
        "n_combinations": len(groups),
        "gaps": gaps, "conflicts": conflicts, "errors": errors,
        "gap_combinations": len(gaps), "conflict_combinations": len(conflicts),
        "redundant_combinations": redundant,
        "gap_probe_rate": gap_probes / n, "conflict_probe_rate": conflict_probes / n,
        "issue_count": len(table.problems) + len(gaps) + len(conflicts) + len(errors),
    }


def issues_text(table, spec, check, max_items=6):
    """Human-readable problem list for the repair prompt."""
    lines = []
    for pr in check["problems"]:
        k = pr["kind"]
        if k == "invalid_condition":
            lines.append(f"Condition {pr['id']} \"{pr['expr']}\" cannot be evaluated: {pr['why']}. "
                         f"Use only the input names and the allowed operators.")
        elif k == "unknown_condition":
            lines.append(f"Rule {pr['id']} refers to condition \"{pr['cond']}\", which is not defined.")
        elif k == "rule_uses_invalid_condition":
            lines.append(f"Rule {pr['id']} uses condition {pr['cond']}, which cannot be evaluated.")
        elif k == "invalid_output":
            lines.append(f"Rule {pr['id']} has output \"{pr['output']}\", which is not an allowed output value.")
        elif k == "invalid_entry":
            lines.append(f"Rule {pr['id']} has an invalid entry {pr['value']} for {pr['cond']} (use true or false).")
        elif k == "no_rules":
            lines.append("The table has no usable rules.")
        elif k == "duplicate_condition_id":
            lines.append(f"Condition id {pr['id']} is used twice.")
    for vec, p in check["errors"][:2]:
        lines.append(f"Some conditions cannot be evaluated for the input {_fmt_inputs(spec, p)}.")
    cond_ids = table.condition_order
    for vec, p, cnt in check["gaps"][:3]:
        truth = ", ".join(f"{c}={'true' if v else 'false'}" for c, v in zip(cond_ids, vec))
        lines.append(f"Missing combination: no rule matches the input {_fmt_inputs(spec, p)} ({truth}).")
    for vec, p, ids, outs, cnt in check["conflicts"][:3]:
        shown = ", ".join(f"{i} gives \"{o}\"" for i, o in zip(ids, outs))
        lines.append(f"Conflict: the input {_fmt_inputs(spec, p)} matches several rules with different "
                     f"outputs ({shown}).")
    head = lines[:max_items]
    if check["gap_combinations"] or check["conflict_combinations"]:
        head.append(f"In total, {check['gap_combinations']} reachable combinations of your conditions match no "
                    f"rule and {check['conflict_combinations']} match rules with different outputs.")
    return head


def gt_table_eval(table, spec, probes, gt_table):
    """Compare an LLM table with the ground truth on the evaluation probes."""
    per_rule = collections.defaultdict(lambda: collections.Counter())
    point = collections.Counter()
    first_hit_ok = 0
    for p in probes:
        _, _, gt_ids = gt_table.decide(p)
        gt_rule = gt_ids[0]
        ref = spec.reference_output(p)
        status, out, _ = table.decide(p)
        if status == "gap":
            kind = "gap"
        elif status == "conflict":
            kind = "conflict"
        else:
            kind = "correct" if out == ref else "wrong"
        point[kind] += 1
        per_rule[gt_rule][kind] += 1
        if table.decide_first_hit(p) == ref:
            first_hit_ok += 1
    n = max(len(probes), 1)
    rules = spec.feasible_gt_rules()
    rules_correct = [r for r in rules if per_rule[r]["correct"] == sum(per_rule[r].values())]
    rules_gap = [r for r in rules if per_rule[r]["gap"] > 0]
    rules_conflict = [r for r in rules if per_rule[r]["conflict"] > 0]
    rules_wrong = [r for r in rules if per_rule[r]["wrong"] > 0]
    return {
        "probe_accuracy": point["correct"] / n,
        "probe_gap_rate": point["gap"] / n,
        "probe_conflict_rate": point["conflict"] / n,
        "probe_wrong_rate": point["wrong"] / n,
        "first_hit_accuracy": first_hit_ok / n,
        "gt_rules": len(rules),
        "rules_fully_correct": len(rules_correct),
        "rules_with_gap": rules_gap,
        "rules_with_conflict": rules_conflict,
        "rules_with_wrong_output": rules_wrong,
        "rule_correctness": len(rules_correct) / len(rules),
    }
