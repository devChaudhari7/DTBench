"""Benchmark data model: input variables, specifications, value coercion."""
import importlib
import math
import re
from dataclasses import dataclass, field

from .expr import compile_condition


@dataclass
class Var:
    name: str
    type: str                  # "int" | "float" | "bool" | "enum"
    lo: float = None
    hi: float = None
    values: tuple = ()
    desc: str = ""

    def describe(self):
        d = f" ({self.desc})" if self.desc else ""
        if self.type == "int":
            return f"- {self.name}: integer from {self.lo} to {self.hi}{d}"
        if self.type == "float":
            return f"- {self.name}: decimal number from {self.lo} to {self.hi}{d}"
        if self.type == "bool":
            return f"- {self.name}: true or false{d}"
        vals = ", ".join(f'"{v}"' for v in self.values)
        return f"- {self.name}: one of {vals}{d}"

    def json_schema(self):
        if self.type == "int":
            return {"type": "integer"}
        if self.type == "float":
            return {"type": "number"}
        if self.type == "bool":
            return {"type": "boolean"}
        return {"type": "string", "enum": list(self.values)}

    # ---- coercion of values written by an LLM -------------------------------------
    def coerce(self, value):
        """Return (ok, canonical_value, reason)."""
        if self.type == "bool":
            if isinstance(value, bool):
                return True, value, ""
            if isinstance(value, (int, float)) and value in (0, 1):
                return True, bool(value), ""
            if isinstance(value, str) and value.strip().lower() in ("true", "yes", "y", "1", "false", "no", "n", "0"):
                return True, value.strip().lower() in ("true", "yes", "y", "1"), ""
            return False, None, f"{self.name}: not a boolean ({value!r})"
        if self.type == "enum":
            if isinstance(value, str):
                for v in self.values:
                    if value.strip().lower() == v.lower():
                        return True, v, ""
            return False, None, f"{self.name}: not one of the allowed values ({value!r})"
        # numeric
        if isinstance(value, bool):
            return False, None, f"{self.name}: boolean given for a number"
        if isinstance(value, str):
            try:
                value = float(value.replace(",", "").strip())
            except ValueError:
                return False, None, f"{self.name}: not a number ({value!r})"
        if not isinstance(value, (int, float)) or (isinstance(value, float) and not math.isfinite(value)):
            return False, None, f"{self.name}: not a number ({value!r})"
        if self.type == "int":
            if isinstance(value, float):
                if not value.is_integer():
                    return False, None, f"{self.name}: not an integer ({value!r})"
                value = int(value)
        else:
            value = float(value)
        if value < self.lo or value > self.hi:
            return False, None, f"{self.name}: {value} outside {self.lo}..{self.hi}"
        return True, value, ""


@dataclass
class Spec:
    id: str
    name: str
    category: str
    source: str
    source_url: str
    rules_text: str
    inputs: list
    output_name: str
    output_type: str               # "enum" | "int"
    output_values: tuple
    gt_table: dict
    reference: str                  # module name inside dtbench.reference
    constraint: str = None          # boolean expression that every valid input must satisfy
    constraint_desc: str = ""
    clarifications: str = ""
    tags: tuple = ()
    extra_probes: object = None     # callable(spec, rng) -> list of input dicts
    _ref = None
    _constraint = None

    # ---- basic helpers -------------------------------------------------------------
    @property
    def var_names(self):
        return [v.name for v in self.inputs]

    def var(self, name):
        for v in self.inputs:
            if v.name == name:
                return v
        raise KeyError(name)

    def reference_fn(self):
        if self._ref is None:
            mod = importlib.import_module(f"dtbench.reference.{self.reference}")
            self._ref = mod.decide
        return self._ref

    def reference_output(self, inputs):
        return self.normalize_output(self.reference_fn()(**inputs))

    def constraint_ok(self, inputs):
        if not self.constraint:
            return True
        if self._constraint is None:
            self._constraint = compile_condition("constraint", self.constraint, self.var_names)
        return self._constraint.evaluate(env_for(self, inputs)) is True

    # ---- data dictionary for prompts -------------------------------------------------
    def describe_inputs(self):
        lines = [v.describe() for v in self.inputs]
        if self.constraint:
            lines.append(f"Constraint on valid inputs: {self.constraint_desc or self.constraint}")
        return "\n".join(lines)

    def describe_output(self):
        if self.output_type == "int":
            return f"- {self.output_name}: an integer"
        vals = ", ".join(f'"{v}"' for v in self.output_values)
        return f"- {self.output_name}: one of {vals}"

    def output_schema(self):
        if self.output_type == "int":
            return {"type": "integer"}
        return {"type": "string", "enum": list(self.output_values)}

    def inputs_schema(self):
        return {
            "type": "object",
            "properties": {v.name: v.json_schema() for v in self.inputs},
            "required": self.var_names,
            "additionalProperties": False,
        }

    # ---- normalisation ----------------------------------------------------------------
    def normalize_output(self, value):
        """Map an output written by an LLM (or the reference code) to a canonical label.

        Returns the canonical label, or ``"INVALID:<text>"`` if it matches nothing.
        """
        if self.output_type == "int":
            if isinstance(value, bool):
                return f"INVALID:{value}"
            if isinstance(value, (int, float)) and float(value).is_integer():
                return str(int(value))
            m = re.fullmatch(r"\s*(-?\d+)(\.0+)?\s*(days?)?\s*", str(value), flags=re.I)
            return m.group(1) if m else f"INVALID:{value}"
        text = str(value).strip().strip('."\'').lower()
        squash = lambda s: re.sub(r"[\s_\-%]+", "", s.lower())
        for v in self.output_values:
            if text == v.lower():
                return v
        for v in self.output_values:
            if squash(text) == squash(v):
                return v
        return f"INVALID:{value}"

    def coerce_inputs(self, raw):
        """Validate a test's inputs. Returns (ok, inputs, reason)."""
        if not isinstance(raw, dict):
            return False, None, "inputs is not an object"
        out = {}
        lower = {str(k).strip().lower(): v for k, v in raw.items()}
        for var in self.inputs:
            if var.name.lower() not in lower:
                return False, None, f"missing input {var.name}"
            ok, val, why = var.coerce(lower[var.name.lower()])
            if not ok:
                return False, None, why
            out[var.name] = val
        if not self.constraint_ok(out):
            return False, None, "violates the input constraint"
        return True, out, ""

    def feasible_gt_rules(self):
        return [r["id"] for r in self.gt_table["rules"] if r.get("feasible", True)]


def env_for(spec, inputs):
    """Evaluation environment for conditions: enum strings lower-cased."""
    env = {}
    for v in spec.inputs:
        x = inputs[v.name]
        env[v.name] = x.lower() if isinstance(x, str) else x
    return env
