"""Verify every ground-truth table against its reference implementation.

For each spec: the ground-truth table must parse cleanly; on every evaluation probe
exactly one rule fires and its output equals the reference implementation; every
feasible rule is exercised by at least one probe; no probe reaches a rule marked infeasible.
"""
import collections
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dtbench.specs import SPECS            # noqa: E402
from dtbench.table import DecisionTable    # noqa: E402
from dtbench.probes import gt_probes       # noqa: E402


def main():
    ok_all = True
    summary = []
    for spec in SPECS:
        t0 = time.time()
        gt = DecisionTable(spec.gt_table, spec)
        assert not gt.problems, (spec.id, gt.problems)
        probes = gt_probes(spec)
        hits = collections.Counter()
        bad = []
        for p in probes:
            status, out, ids = gt.decide(p)
            ref = spec.reference_output(p)
            if status != "ok" or len(ids) != 1 or out != ref:
                bad.append((p, status, out, ids, ref))
            else:
                hits[ids[0]] += 1
        infeasible_hit = 0
        for inf in spec.gt_table.get("infeasible_rules", []):
            for p in probes:
                vec = dict(zip(gt.condition_order, gt.condition_vector(p)))
                if all(vec[k] is v for k, v in inf["when"].items()):
                    infeasible_hit += 1
        missing = [r for r in spec.feasible_gt_rules() if hits[r] < 1]
        ok = not bad and not missing and infeasible_hit == 0
        ok_all &= ok
        summary.append({"spec": spec.id, "probes": len(probes), "rules": len(spec.gt_table["rules"]),
                        "min_hits": min(hits.values()) if hits else 0, "mismatches": len(bad),
                        "rules_under_3_hits": missing, "infeasible_hits": infeasible_hit,
                        "seconds": round(time.time() - t0, 1)})
        print(f"{spec.id} {spec.name:28s} probes={len(probes):6d} rules={len(spec.gt_table['rules']):2d} "
              f"min_hits={summary[-1]['min_hits']:5d} mismatches={len(bad)} missing={missing} "
              f"infeasible_hits={infeasible_hit} {'OK' if ok else 'FAIL'}")
        for b in bad[:5]:
            print("   mismatch:", b)
    print("ALL OK" if ok_all else "SOME FAILED")
    return ok_all


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
