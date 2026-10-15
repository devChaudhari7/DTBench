"""Predicate-guided probe synthesis.

Given the condition expressions of a decision table, build a set of concrete
inputs ("probes") that exercises the boundaries the conditions talk about:

1. per-variable candidates: domain extremes, mid-point, every constant the
   conditions compare a variable with (c-1, c, c+1 for integers; c +/- 0.01 for
   decimals), members of ``in (...)`` sets, and multiples for ``v % k`` tests;
2. the Cartesian product of the candidates (sampled when too large);
3. relation solving: for comparisons between expressions over several
   variables (``a + b > c``, ``weight / (length * length) > 30``) the equality
   point is solved for each variable in which the expression is linear;
4. uniform random inputs.

Invalid inputs (outside the domain or violating the spec constraint) are dropped.
The same algorithm is used on the ground-truth table (to build the evaluation
probe set) and on an LLM's own table (ground-truth-free validation).
"""
import ast
import itertools
import math
import random

from .expr import SAFE_GLOBALS
from .model import env_for


def _num(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = _num(node.operand)
        return -v if v is not None else None
    return None


def analyse(trees, spec):
    consts = {v: set() for v in spec.var_names}
    members = {v: set() for v in spec.var_names}
    mods = {v: set() for v in spec.var_names}
    relations = []
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                items = [node.left] + list(node.comparators)
                for left, op, right in zip(items, node.ops, items[1:]):
                    lname = left.id if isinstance(left, ast.Name) else None
                    rname = right.id if isinstance(right, ast.Name) else None
                    lc, rc = _num(left), _num(right)
                    if isinstance(op, (ast.In, ast.NotIn)):
                        if lname and isinstance(right, (ast.Tuple, ast.List, ast.Set)):
                            for e in right.elts:
                                c = _num(e)
                                if c is not None:
                                    members[lname].add(c)
                        continue
                    if lname and rc is not None:
                        consts[lname].add(rc)
                    elif rname and lc is not None:
                        consts[rname].add(lc)
                    else:
                        names = {n.id for n in ast.walk(left) if isinstance(n, ast.Name)}
                        names |= {n.id for n in ast.walk(right) if isinstance(n, ast.Name)}
                        if names:
                            relations.append((left, right, names))
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Name):
                k = _num(node.right)
                if k and k > 0:
                    mods[node.left.id].add(k)
    return consts, members, mods, relations


def candidates(var, consts, members, mods, rng):
    if var.type == "bool":
        return [False, True]
    if var.type == "enum":
        return list(var.values)
    vals = set()
    if var.type == "int":
        lo, hi = int(var.lo), int(var.hi)
        vals |= {lo, lo + 1, hi - 1, hi, (lo + hi) // 2}
        for c in consts | members:
            for x in (math.floor(c) - 1, math.floor(c), math.ceil(c), math.ceil(c) + 1):
                vals.add(int(x))
        for k in mods:
            k = int(k)
            if k <= 0:
                continue
            first = lo + (-lo) % k
            mid = (lo + hi) // 2
            middle = mid + (-mid) % k
            last = hi - hi % k
            for x in (first, middle, last):
                vals |= {x - 1, x, x + 1}
        vals |= {rng.randint(lo, hi) for _ in range(2)}
        return sorted(x for x in vals if lo <= x <= hi)
    lo, hi = float(var.lo), float(var.hi)
    vals |= {lo, hi, round((lo + hi) / 2, 2)}
    for c in consts | members:
        for d in (-0.5, -0.01, 0.0, 0.01, 0.5):
            vals.add(round(c + d, 6))
    vals |= {round(rng.uniform(lo, hi), 2) for _ in range(2)}
    return sorted(x for x in vals if lo <= x <= hi)


def random_point(spec, rng):
    p = {}
    for v in spec.inputs:
        if v.type == "int":
            p[v.name] = rng.randint(int(v.lo), int(v.hi))
        elif v.type == "float":
            p[v.name] = round(rng.uniform(v.lo, v.hi), 2)
        elif v.type == "bool":
            p[v.name] = rng.random() < 0.5
        else:
            p[v.name] = rng.choice(v.values)
    return p


def product_points(spec, cands, max_n, rng):
    size = 1
    for c in cands:
        size *= len(c)
    names = spec.var_names
    if size <= max_n:
        return [dict(zip(names, combo)) for combo in itertools.product(*cands)]
    seen, pts = set(), []
    tries = 0
    while len(pts) < max_n and tries < max_n * 5:
        tries += 1
        combo = tuple(rng.choice(c) for c in cands)
        if combo not in seen:
            seen.add(combo)
            pts.append(dict(zip(names, combo)))
    return pts


def solve_relations(spec, relations, rng, n_per_relation):
    pts = []
    numeric = {v.name for v in spec.inputs if v.type in ("int", "float")}
    for left, right, names in relations:
        expr = ast.fix_missing_locations(ast.Expression(ast.BinOp(left=left, op=ast.Sub(), right=right)))
        try:
            code = compile(expr, "<relation>", "eval")
        except Exception:
            continue
        targets = sorted(n for n in names if n in numeric)
        for _ in range(n_per_relation):
            base = random_point(spec, rng)
            for x in targets:
                var = spec.var(x)

                def f(val):
                    try:
                        return float(eval(code, SAFE_GLOBALS, env_for(spec, {**base, x: val})))
                    except Exception:
                        return None
                a, b = var.lo, var.hi
                fa, fb = f(a), f(b)
                if fa is None or fb is None or fa == fb:
                    continue
                root = a - fa * (b - a) / (fb - fa)
                fr = f(root)
                if fr is None or abs(fr) > 1e-6 * (1 + abs(fa) + abs(fb)):
                    continue            # not linear in x: skip
                if var.type == "int":
                    r0 = int(round(root))
                    vals = (r0 - 1, r0, r0 + 1)
                else:
                    vals = (root, round(root - 0.01, 6), round(root + 0.01, 6))
                for val in vals:
                    if var.lo <= val <= var.hi:
                        pts.append({**base, x: val})
    return pts


def _key(p, names):
    return tuple(round(p[n], 9) if isinstance(p[n], float) else p[n] for n in names)


def clean(spec, points):
    names = spec.var_names
    seen, out = set(), []
    for p in points:
        ok = True
        for v in spec.inputs:
            x = p[v.name]
            if v.type in ("int", "float") and not (v.lo <= x <= v.hi):
                ok = False
                break
        if not ok or not spec.constraint_ok(p):
            continue
        k = _key(p, names)
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def synthesize(spec, trees, seed=0, max_product=8000, n_relation=60, n_random=1500):
    rng = random.Random(seed)
    consts, members, mods, relations = analyse(trees, spec)
    cands = [candidates(v, consts[v.name], members[v.name], mods[v.name], rng) for v in spec.inputs]
    pts = product_points(spec, cands, max_product, rng)
    pts += solve_relations(spec, relations, rng, n_relation)
    pts += [random_point(spec, rng) for _ in range(n_random)]
    return clean(spec, pts)


def gt_probes(spec, seed=12345):
    """Evaluation probe set for a spec: synthesis on the ground-truth table + spec extras."""
    from .table import DecisionTable
    gt = DecisionTable(spec.gt_table, spec)
    trees = [c.tree for c in gt.conditions.values()]
    if spec.constraint:
        from .expr import parse_expr
        trees.append(parse_expr(spec.constraint, spec.var_names))
    pts = synthesize(spec, trees, seed=seed, max_product=20000, n_relation=250, n_random=4000)
    if spec.extra_probes:
        pts += spec.extra_probes(spec, random.Random(seed + 1))
    return clean(spec, pts)
