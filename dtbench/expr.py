"""Safe parsing and evaluation of decision-table condition expressions.

A condition is a Python-style boolean expression over the declared input
variables, e.g. ``age >= 18``, ``weather == "rainy"``, ``a + b > c`` or
``month in (4, 6, 9, 11)``. Expressions are parsed with :mod:`ast`, checked
against a whitelist of node types (no calls, attributes or subscripts), and
only then compiled. String constants are lower-cased so that comparisons with
enumerated input values are case-insensitive.
"""
import ast
import re

ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
    ast.Name, ast.Load, ast.Constant, ast.Tuple, ast.List, ast.Set,
)

SAFE_GLOBALS = {"__builtins__": {}}


class ExprError(Exception):
    """Raised when a condition expression cannot be used."""


def normalize_source(src):
    """Repair common non-Python spellings produced by LLMs (AND, &&, =, true ...)."""
    s = str(src).strip()
    s = s.replace("≥", ">=").replace("≤", "<=").replace("≠", "!=")
    s = s.replace("&&", " and ").replace("||", " or ")
    s = re.sub(r"\bAND\b", "and", s)
    s = re.sub(r"\bOR\b", "or", s)
    s = re.sub(r"\bNOT\b", "not", s)
    s = re.sub(r"\btrue\b", "True", s, flags=re.IGNORECASE)
    s = re.sub(r"\bfalse\b", "False", s, flags=re.IGNORECASE)
    s = re.sub(r"!(?!=)", " not ", s)                 # !x  -> not x
    s = re.sub(r"(?<![<>=!])=(?!=)", "==", s)         # a = b -> a == b
    return s


class _LowerStrings(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str):
            return ast.copy_location(ast.Constant(node.value.strip().lower()), node)
        return node


def parse_expr(src, var_names):
    """Return a validated AST (``ast.Expression``) for ``src``.

    Raises ExprError for syntax errors, disallowed constructs or unknown names.
    """
    text = normalize_source(src)
    if not text:
        raise ExprError("empty condition")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise ExprError(f"syntax error ({exc.msg})")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ExprError(f"unsupported construct '{type(node).__name__}'")
        if isinstance(node, ast.Name) and node.id not in var_names:
            raise ExprError(f"unknown name '{node.id}'")
    tree = ast.fix_missing_locations(_LowerStrings().visit(tree))
    return tree


class Condition:
    """A compiled condition: ``evaluate(env)`` returns True, False or None (runtime error)."""

    def __init__(self, cid, src, var_names):
        self.id = cid
        self.src = src
        self.tree = parse_expr(src, var_names)
        self.text = ast.unparse(self.tree)
        self.code = compile(self.tree, "<condition>", "eval")

    def evaluate(self, env):
        try:
            return bool(eval(self.code, SAFE_GLOBALS, env))
        except Exception:
            return None


def compile_condition(cid, src, var_names):
    return Condition(cid, src, var_names)
