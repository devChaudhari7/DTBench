"""Prompt templates and JSON schemas for the three generation strategies.

P0  direct      - rules -> test cases (decision-table technique named, no explicit table)
P1  table-first - rules -> decision table -> one test case per rule
P2  validated   - P1 table -> ground-truth-free structural check -> repair (<= 2 rounds) -> test cases

All prompts for one spec share the same prefix (system message + spec block),
so the inference server can reuse its prompt cache across calls.
"""
import json

SYSTEM = ("You are an expert software test engineer who designs test cases with the decision table "
          "technique. Reply with JSON only.")

CONDITION_SYNTAX = (
    "Each condition is a yes/no test written as a Python boolean expression that uses only the input names "
    "above, numbers, quoted text values, and the operators < <= > >= == != and or not + - * / % in. "
    "Examples: \"age >= 18\", \"weather == 'rainy'\", \"a + b > c\", \"month in (4, 6, 9, 11)\".")


def spec_block(spec):
    return (f"BUSINESS RULES\n{spec.rules_text}\n\n"
            f"INPUTS\n{spec.describe_inputs()}\n\n"
            f"OUTPUT\n{spec.describe_output()}\n\n")


def _messages(spec, task):
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": spec_block(spec) + "TASK\n" + task}]


def table_task():
    return (
        "Build a decision table for these business rules.\n"
        "Return JSON with:\n"
        "- \"conditions\": a list of {\"id\": \"C1\", \"expr\": \"<condition>\"}. " + CONDITION_SYNTAX + "\n"
        "- \"rules\": a list of {\"id\": \"R1\", \"when\": {\"C1\": true, \"C2\": false}, \"output\": <output value>}. "
        "In \"when\", list only the conditions that matter for the rule; conditions left out are \"don't care\".\n"
        "Every valid input must match exactly one rule: the table must be complete, and rules must not overlap "
        "with different outputs.")


def tests_from_table_task(table_json):
    return (
        "Below is the decision table you built for these business rules. Derive the test cases: write one test "
        "case for every rule, with concrete values for ALL inputs that satisfy the rule's conditions, and the "
        "expected output.\n"
        "Return JSON: {\"tests\": [{\"rule\": \"R1\", \"inputs\": {<every input name>: <value>}, "
        "\"expected\": <output value>}]}\n\n"
        "DECISION TABLE\n" + json.dumps(table_json, ensure_ascii=False, separators=(',', ':')))


def direct_task():
    return (
        "Design test cases for these business rules using the decision table testing technique: identify the "
        "conditions and cover every combination of conditions that leads to a distinct rule, with one test case "
        "per rule. Give concrete values for ALL inputs and the expected output.\n"
        "Return JSON: {\"tests\": [{\"inputs\": {<every input name>: <value>}, \"expected\": <output value>}]}")


def repair_task(table_json, issue_lines):
    issues = "\n".join(f"- {line}" for line in issue_lines)
    return (
        "Below is the decision table you built for these business rules. An automated checker evaluated it on "
        "many input values and found the problems listed after it. Fix the table so that every valid input "
        "matches exactly one rule and the outputs follow the business rules. Return the complete corrected "
        "table as JSON in the same format: {\"conditions\": [{\"id\", \"expr\"}], \"rules\": [{\"id\", \"when\", "
        "\"output\"}]}. " + CONDITION_SYNTAX + "\n\n"
        "DECISION TABLE\n" + json.dumps(table_json, ensure_ascii=False, separators=(',', ':')) + "\n\n"
        "PROBLEMS FOUND\n" + issues)


def table_messages(spec):
    return _messages(spec, table_task())


def tests_from_table_messages(spec, table_json):
    return _messages(spec, tests_from_table_task(table_json))


def direct_messages(spec):
    return _messages(spec, direct_task())


def repair_messages(spec, table_json, issue_lines):
    return _messages(spec, repair_task(table_json, issue_lines))


# ---------------------------------------------------------------------------------------
# JSON schemas (enforced with grammar-constrained decoding). Types and enumerations are
# enforced; numeric ranges are not, so out-of-domain inputs remain measurable.
# ---------------------------------------------------------------------------------------
MAX_RULES = 48
MAX_TESTS = 48


def table_schema(spec):
    return {
        "type": "object",
        "properties": {
            "conditions": {
                "type": "array", "minItems": 1, "maxItems": 16,
                "items": {"type": "object",
                          "properties": {"id": {"type": "string"}, "expr": {"type": "string"}},
                          "required": ["id", "expr"], "additionalProperties": False}},
            "rules": {
                "type": "array", "minItems": 1, "maxItems": MAX_RULES,
                "items": {"type": "object",
                          "properties": {"id": {"type": "string"},
                                         "when": {"type": "object", "additionalProperties": {"type": "boolean"}},
                                         "output": spec.output_schema()},
                          "required": ["id", "when", "output"], "additionalProperties": False}},
        },
        "required": ["conditions", "rules"], "additionalProperties": False,
    }


def tests_schema(spec, with_rule=True):
    props, req = {}, []
    if with_rule:
        props["rule"] = {"type": "string"}
        req.append("rule")
    props["inputs"] = spec.inputs_schema()
    props["expected"] = spec.output_schema()
    req += ["inputs", "expected"]
    return {
        "type": "object",
        "properties": {"tests": {"type": "array", "minItems": 1, "maxItems": MAX_TESTS,
                                 "items": {"type": "object", "properties": props, "required": req,
                                           "additionalProperties": False}}},
        "required": ["tests"], "additionalProperties": False,
    }
