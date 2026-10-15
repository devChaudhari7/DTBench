"""Assessment of LLM-generated test suites against the ground truth."""
from .mutation import kills


def assess_tests(raw_tests, spec, gt_table, mutants, own_table=None):
    """Return metrics for a list of test dicts {"inputs": {...}, "expected": ...}.

    * valid: every input present, typed and inside its domain (and the constraint holds)
    * correct: valid and the expected output equals the reference implementation
    * rule coverage: share of feasible ground-truth rules exercised by >=1 correct test
    * missed combinations: feasible ground-truth rules with no correct test
    * mutation score: share of non-equivalent mutants killed by the correct tests
    """
    rules = spec.feasible_gt_rules()
    n = 0
    valid, correct = [], []
    invalid_reasons = []
    covered_any, covered_correct = set(), set()
    redundant = 0
    consistent_with_own_table = checked_own = 0
    for t in raw_tests or []:
        if not isinstance(t, dict):
            n += 1
            invalid_reasons.append("test is not an object")
            continue
        n += 1
        ok, inputs, why = spec.coerce_inputs(t.get("inputs"))
        if not ok:
            invalid_reasons.append(why)
            continue
        expected = spec.normalize_output(t.get("expected"))
        _, _, ids = gt_table.decide(inputs)
        if len(ids) != 1:                      # cannot happen for a verified ground truth; guard anyway
            invalid_reasons.append("no unique ground-truth rule")
            continue
        gt_rule = ids[0]
        valid.append((inputs, expected, gt_rule))
        covered_any.add(gt_rule)
        if own_table is not None and own_table.usable:
            checked_own += 1
            status, out, _ = own_table.decide(inputs)
            if status == "ok" and out == expected:
                consistent_with_own_table += 1
        if expected == spec.reference_output(inputs):
            if gt_rule in covered_correct:
                redundant += 1
            covered_correct.add(gt_rule)
            correct.append((inputs, expected))
    live = [m for m in mutants if not m.equivalent]
    killed = kills(spec, mutants, correct) if correct else set()
    return {
        "n_tests": n,
        "n_valid": len(valid),
        "n_correct": len(correct),
        "validity": len(valid) / n if n else 0.0,
        "oracle_accuracy": len(correct) / len(valid) if valid else 0.0,
        "rule_coverage": len(covered_correct) / len(rules),
        "input_rule_coverage": len(covered_any) / len(rules),
        "missed_rules": [r for r in rules if r not in covered_correct],
        "n_missed": len([r for r in rules if r not in covered_correct]),
        "redundancy": redundant / len(correct) if correct else 0.0,
        "mutants": len(live),
        "killed": len(killed),
        "mutation_score": len(killed) / len(live) if live else 0.0,
        "own_table_consistency": consistent_with_own_table / checked_own if checked_own else None,
        "invalid_reasons": invalid_reasons[:10],
    }
