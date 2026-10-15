"""Executable limited-entry decision tables.

JSON format (used for ground truth and for LLM output):

    {"conditions": [{"id": "C1", "expr": "age >= 18"}, ...],
     "rules": [{"id": "R1", "when": {"C1": true, "C2": false}, "output": "Eligible"}, ...]}

Conditions not listed in a rule's ``when`` are "don't care". Ground-truth rules
may carry ``"feasible": false`` for combinations that no valid input can reach.
"""
import re

from .expr import ExprError, compile_condition
from .model import env_for


def _bool_entry(v):
    """Interpret an entry value; None means don't care, 'bad' means unusable."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("t", "true", "y", "yes", "1"):
            return True
        if s in ("f", "false", "n", "no", "0"):
            return False
        if s in ("-", "", "any", "dc", "don't care", "dont care", "*", "x", "n/a"):
            return None
    if v is None:
        return None
    return "bad"


class Rule:
    def __init__(self, rid, entries, output, valid, raw_output, feasible=True):
        self.id = rid
        self.entries = entries          # {condition_id: bool}
        self.output = output            # canonical label or "INVALID:..."
        self.valid = valid
        self.raw_output = raw_output
        self.feasible = feasible


class DecisionTable:
    def __init__(self, data, spec):
        self.spec = spec
        self.problems = []              # list of dicts {kind, ...}
        self.conditions = {}
        self.condition_order = []
        if not isinstance(data, dict):
            self.problems.append({"kind": "not_a_table"})
            data = {}
        expr_index = {}
        for i, c in enumerate(data.get("conditions") or []):
            if not isinstance(c, dict):
                self.problems.append({"kind": "invalid_condition", "id": f"#{i+1}", "expr": str(c), "why": "not an object"})
                continue
            cid = str(c.get("id", f"C{i+1}")).strip() or f"C{i+1}"
            src = c.get("expr", "")
            try:
                cond = compile_condition(cid, src, spec.var_names)
            except ExprError as exc:
                self.problems.append({"kind": "invalid_condition", "id": cid, "expr": str(src), "why": str(exc)})
                continue
            if cid in self.conditions:
                self.problems.append({"kind": "duplicate_condition_id", "id": cid})
                continue
            self.conditions[cid] = cond
            self.condition_order.append(cid)
            expr_index[re.sub(r"\s+", "", cond.text)] = cid
        invalid_ids = {p["id"] for p in self.problems if p["kind"] == "invalid_condition"}
        self.rules = []
        for i, r in enumerate(data.get("rules") or []):
            if not isinstance(r, dict):
                self.problems.append({"kind": "invalid_rule", "id": f"#{i+1}", "why": "not an object"})
                continue
            rid = str(r.get("id", f"R{i+1}")).strip() or f"R{i+1}"
            raw_out = r.get("output")
            output = spec.normalize_output(raw_out)
            valid = True
            entries = {}
            when = r.get("when") or {}
            if not isinstance(when, dict):
                self.problems.append({"kind": "invalid_rule", "id": rid, "why": "'when' is not an object"})
                when, valid = {}, False
            for key, val in when.items():
                k = str(key).strip()
                if k not in self.conditions:
                    alt = expr_index.get(re.sub(r"\s+", "", str(key)))
                    if alt:
                        k = alt
                    elif k in invalid_ids:
                        self.problems.append({"kind": "rule_uses_invalid_condition", "id": rid, "cond": k})
                        valid = False
                        continue
                    else:
                        self.problems.append({"kind": "unknown_condition", "id": rid, "cond": str(key)})
                        valid = False
                        continue
                b = _bool_entry(val)
                if b == "bad":
                    self.problems.append({"kind": "invalid_entry", "id": rid, "cond": k, "value": repr(val)})
                    valid = False
                elif b is not None:
                    entries[k] = b
            if output.startswith("INVALID:"):
                self.problems.append({"kind": "invalid_output", "id": rid, "output": str(raw_out)})
            self.rules.append(Rule(rid, entries, output, valid, raw_out, r.get("feasible", True)))
        if not self.rules:
            self.problems.append({"kind": "no_rules"})

    # ------------------------------------------------------------------------------------
    @property
    def usable(self):
        return any(r.valid for r in self.rules) and bool(self.conditions)

    def condition_vector(self, inputs):
        env = env_for(self.spec, inputs)
        return tuple(self.conditions[c].evaluate(env) for c in self.condition_order)

    def fired_from_vector(self, vec):
        values = dict(zip(self.condition_order, vec))
        fired = []
        for idx, r in enumerate(self.rules):
            if not r.valid:
                continue
            if all(values.get(k) is v for k, v in r.entries.items()):
                fired.append(idx)
        return fired

    def fired(self, inputs):
        return self.fired_from_vector(self.condition_vector(inputs))

    def decide(self, inputs):
        """Unique-hit semantics. Returns (status, output, fired_rule_ids).

        status: "ok" (one output), "gap" (no rule), "conflict" (different outputs).
        Overlapping rules that agree on the output count as "ok" (redundant, not inconsistent).
        """
        idx = self.fired(inputs)
        if not idx:
            return "gap", None, []
        outs = {self.rules[i].output for i in idx}
        ids = [self.rules[i].id for i in idx]
        if len(outs) > 1:
            return "conflict", None, ids
        return "ok", outs.pop(), ids

    def decide_first_hit(self, inputs):
        idx = self.fired(inputs)
        return self.rules[idx[0]].output if idx else None

    def to_json(self):
        return {
            "conditions": [{"id": c, "expr": self.conditions[c].text} for c in self.condition_order],
            "rules": [{"id": r.id, "when": r.entries, "output": r.raw_output} for r in self.rules],
        }

    def matrix(self):
        """Rows = conditions, columns = rules, entries T/F/- (for printing)."""
        rows = []
        for c in self.condition_order:
            rows.append([c, self.conditions[c].text] + [
                ("T" if r.entries.get(c) is True else "F" if r.entries.get(c) is False else "-") for r in self.rules])
        rows.append(["", "output"] + [r.raw_output for r in self.rules])
        return rows
