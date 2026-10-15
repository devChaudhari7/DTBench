"""First-order mutation analysis of the reference implementations.

Operators: ROR (relational operator replacement), LCR (logical connector
replacement), AOR (arithmetic operator replacement), CRP (numeric constant +/- 1,
or +/- 0.1 for decimals), RVR (returned output label replaced by another label),
NEG (negate an if-condition) and NDL (delete a 'not').

A mutant that produces the same output as the original on every evaluation
probe is treated as equivalent and excluded from the mutation score.
"""
import ast
import copy
import importlib
import inspect

ROR = {ast.Lt: (ast.LtE, ast.GtE), ast.LtE: (ast.Lt, ast.Gt), ast.Gt: (ast.GtE, ast.LtE),
       ast.GtE: (ast.Gt, ast.Lt), ast.Eq: (ast.NotEq,), ast.NotEq: (ast.Eq,),
       ast.In: (ast.NotIn,), ast.NotIn: (ast.In,)}
AOR = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult}
SYM = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!=",
       ast.In: "in", ast.NotIn: "not in", ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/",
       ast.And: "and", ast.Or: "or"}


def _sites(tree, labels):
    """Yield (node_index, operator, payload, description) for every mutation site."""
    nodes = list(ast.walk(tree))
    returns_with_labels = set()
    for n in nodes:
        if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant) and n.value.value in labels:
            returns_with_labels.add(id(n.value))
    for i, n in enumerate(nodes):
        line = getattr(n, "lineno", 0)
        if isinstance(n, ast.Compare):
            for k, op in enumerate(n.ops):
                for rep in ROR.get(type(op), ()):
                    yield i, "ROR", (k, rep), f"line {line}: '{SYM[type(op)]}' -> '{SYM[rep]}'"
        elif isinstance(n, ast.BoolOp):
            rep = ast.Or if isinstance(n.op, ast.And) else ast.And
            yield i, "LCR", rep, f"line {line}: '{SYM[type(n.op)]}' -> '{SYM[rep]}'"
        elif isinstance(n, ast.BinOp) and type(n.op) in AOR:
            rep = AOR[type(n.op)]
            yield i, "AOR", rep, f"line {line}: '{SYM[type(n.op)]}' -> '{SYM[rep]}'"
        elif isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            step = 1 if isinstance(n.value, int) else 0.1
            for d in (step, -step):
                new = round(n.value + d, 6)
                yield i, "CRP", new, f"line {line}: constant {n.value} -> {new}"
        elif isinstance(n, ast.Constant) and id(n) in returns_with_labels:
            k = labels.index(n.value)
            new = labels[(k + 1) % len(labels)]
            yield i, "RVR", new, f"line {line}: return \"{n.value}\" -> \"{new}\""
        elif isinstance(n, ast.If):
            yield i, "NEG", None, f"line {line}: if-condition negated"
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            yield i, "NDL", None, f"line {line}: 'not' removed"


def _apply(tree, index, op, payload):
    t = copy.deepcopy(tree)
    nodes = list(ast.walk(t))
    n = nodes[index]
    if op == "ROR":
        k, rep = payload
        n.ops[k] = rep()
    elif op == "LCR":
        n.op = payload()
    elif op == "AOR":
        n.op = payload()
    elif op in ("CRP", "RVR"):
        n.value = payload
    elif op == "NEG":
        n.test = ast.UnaryOp(op=ast.Not(), operand=n.test)
    elif op == "NDL":
        for parent in nodes:
            for field, value in ast.iter_fields(parent):
                if value is n:
                    setattr(parent, field, n.operand)
                elif isinstance(value, list):
                    for j, item in enumerate(value):
                        if item is n:
                            value[j] = n.operand
    return ast.fix_missing_locations(t)


class Mutant:
    def __init__(self, mid, op, desc, fn):
        self.id, self.op, self.desc, self.fn = mid, op, desc, fn
        self.equivalent = False


def generate(spec):
    module = importlib.import_module(f"dtbench.reference.{spec.reference}")
    source = inspect.getsource(module)
    tree = ast.parse(source)
    labels = list(spec.output_values)
    mutants = []
    for n, (index, op, payload, desc) in enumerate(_sites(tree, labels)):
        try:
            mt = _apply(tree, index, op, payload)
            code = compile(mt, f"<mutant {spec.id}-{n}>", "exec")
            ns = {}
            exec(code, ns)
            fn = ns["decide"]
        except Exception:
            continue
        mutants.append(Mutant(f"{spec.id}-M{len(mutants)+1:02d}", op, desc, fn))
    return mutants


def run_mutant(spec, mutant, inputs):
    try:
        return spec.normalize_output(mutant.fn(**inputs))
    except Exception as exc:
        return f"EXCEPTION:{type(exc).__name__}"


def mark_equivalents(spec, mutants, probes):
    """Flag mutants indistinguishable from the original on all probes."""
    ref = [spec.reference_output(p) for p in probes]
    for m in mutants:
        m.equivalent = all(run_mutant(spec, m, p) == r for p, r in zip(probes, ref))
    return mutants


def kills(spec, mutants, tests):
    """tests: list of (inputs, expected_label) with correct oracles. Returns killed mutant ids."""
    killed = set()
    for m in mutants:
        if m.equivalent:
            continue
        for inputs, expected in tests:
            if run_mutant(spec, m, inputs) != expected:
                killed.add(m.id)
                break
    return killed
