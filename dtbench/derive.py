"""Mechanical derivation of test cases from a decision table (one test per rule).

For every usable rule, the first input that satisfies the rule's condition entries
is taken from (1) uniformly random inputs, then (2) predicate-guided probes of the
table's own conditions; the expected output is the rule's output. No ground truth is
used. The same procedure is applied to LLM tables and to the ground-truth table, so
differences between suites come only from the tables.
"""
import random

from .expr import parse_expr
from .probes import random_point, synthesize, clean


def derive_tests(table, spec, seed=11, n_random=3000):
    if not table.usable:
        return []
    rng = random.Random(seed)
    randoms = clean(spec, [random_point(spec, rng) for _ in range(n_random)])
    trees = [c.tree for c in table.conditions.values()]
    if spec.constraint:
        trees.append(parse_expr(spec.constraint, spec.var_names))
    probes = synthesize(spec, trees, seed=seed, max_product=6000, n_relation=50, n_random=0)
    rng.shuffle(probes)
    pool = randoms + probes
    vectors = [dict(zip(table.condition_order, table.condition_vector(p))) for p in pool]
    tests = []
    for rule in table.rules:
        if not rule.valid:
            continue
        for p, vec in zip(pool, vectors):
            if all(vec.get(k) is v for k, v in rule.entries.items()):
                tests.append({"rule": rule.id, "inputs": p, "expected": rule.raw_output})
                break
    return tests
