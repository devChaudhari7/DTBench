"""Experiment runner: LLM calls for the three strategies with one model.

P0 asks the model for test cases directly. P1 asks for a decision table. P2 checks the
P1 table with the ground-truth-free structural validator and asks the model to repair it
(at most two rounds). Test cases for P1 and P2 are derived from the tables mechanically
(dtbench.derive), so the model is called 2 to 4 times per specification.

Usage (with an OpenAI-compatible server already running, e.g. llama.cpp llama-server):

    python -m dtbench.runner --model qwen3-4b --base-url http://127.0.0.1:8080/v1 --specs all

Every LLM call is cached under results/raw/<model>/<spec>/<step>.json, so the run can be
resumed and the analysis can be repeated without calling the model again.
"""
import argparse
import json
import pathlib
import time

from . import prompts
from .llm import LLMClient, parse_json
from .specs import SPECS, SPEC_BY_ID
from .table import DecisionTable
from .validator import issues_text, structural_check

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAX_REPAIR_ROUNDS = 2


def _call(client, path, messages, schema, log, grammar=None):
    if path.exists():
        rec = json.loads(path.read_text())
        log(f"  cached {path.parent.name}/{path.stem}")
        return rec
    t0 = time.time()
    try:
        resp = client.chat(messages, schema=schema, grammar=grammar)
    except Exception as exc:
        # server unreachable or timed out: do not cache, stop the run so it can be resumed
        log(f"  {path.parent.name}/{path.stem}: FAILED after {time.time() - t0:.0f}s: {type(exc).__name__}: {exc}")
        raise
    parsed, perr = parse_json(resp["text"])
    rec = {"messages": messages, "response": resp["text"], "finish_reason": resp.get("finish_reason"),
           "usage": resp.get("usage"), "timings": resp.get("timings"), "seconds": resp.get("seconds"),
           "parsed": parsed, "parse_error": perr}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    u = resp.get("usage") or {}
    log(f"  {path.parent.name}/{path.stem}: {resp.get('seconds')}s prompt={u.get('prompt_tokens')} "
        f"completion={u.get('completion_tokens')} finish={resp.get('finish_reason')} "
        f"{'PARSE-ERROR ' + str(perr) if perr else 'ok'}")
    return rec


def _grammar(grammar_dir, spec, kind):
    """Pre-generated GBNF equivalent to the JSON schema (compact JSON), for llama.cpp release builds."""
    if not grammar_dir:
        return None
    return (pathlib.Path(grammar_dir) / f"{spec.id}_{kind}.gbnf").read_text()


def run_spec(client, spec, outdir, log, grammar_dir=None):
    d = outdir / spec.id
    # P0: direct test generation
    _call(client, d / "P0_tests.json", prompts.direct_messages(spec), prompts.tests_schema(spec, with_rule=False), log,
          grammar=_grammar(grammar_dir, spec, "tests"))
    # P1: decision table first, then one test per rule
    t1 = _call(client, d / "P1_table.json", prompts.table_messages(spec), prompts.table_schema(spec), log,
               grammar=_grammar(grammar_dir, spec, "table"))
    table1 = t1["parsed"]
    # P2: ground-truth-free validation and repair, then tests from the final table
    table = table1
    history = []
    for rnd in range(1, MAX_REPAIR_ROUNDS + 1):
        if not isinstance(table, dict):
            break
        dt = DecisionTable(table, spec)
        check = structural_check(dt, spec)
        lines = issues_text(dt, spec, check)
        history.append({"round": rnd, "issues": lines, "gap_combinations": check["gap_combinations"],
                        "conflict_combinations": check["conflict_combinations"],
                        "problems": len(check["problems"])})
        if not lines:
            break
        rec = _call(client, d / f"P2_repair{rnd}.json", prompts.repair_messages(spec, table, lines),
                    prompts.table_schema(spec), log, grammar=_grammar(grammar_dir, spec, "table"))
        if not isinstance(rec["parsed"], dict):
            history[-1]["repair_failed"] = rec["parse_error"]
            break
        table = rec["parsed"]
    else:
        if isinstance(table, dict):
            dt = DecisionTable(table, spec)
            check = structural_check(dt, spec)
            history.append({"round": MAX_REPAIR_ROUNDS + 1, "issues": issues_text(dt, spec, check),
                            "gap_combinations": check["gap_combinations"],
                            "conflict_combinations": check["conflict_combinations"],
                            "problems": len(check["problems"]), "final_check_only": True})
    changed = table is not table1
    (d / "P2_summary.json").write_text(json.dumps({"final_table": table, "changed": changed,
                                                   "history": history}, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="label used for the results folder")
    ap.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    ap.add_argument("--api-model", default="local", help="model name sent to the API")
    ap.add_argument("--specs", default="all")
    ap.add_argument("--out", default=str(ROOT / "results" / "raw"))
    ap.add_argument("--grammar-dir", default=None,
                    help="send pre-generated GBNF grammars (dtbench/grammars) instead of JSON schemas")
    args = ap.parse_args()
    specs = SPECS if args.specs == "all" else [SPEC_BY_ID[s] for s in args.specs.split(",")]
    client = LLMClient(args.base_url, model=args.api_model)
    outdir = pathlib.Path(args.out) / args.model
    logf = open(outdir.parent / f"{args.model}.log", "a") if outdir.parent.exists() else None

    def log(msg):
        line = time.strftime("%H:%M:%S ") + msg
        print(line, flush=True)
        if logf:
            logf.write(line + "\n")
            logf.flush()
    outdir.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        log(f"{args.model} {spec.id} {spec.name}")
        try:
            run_spec(client, spec, outdir, log, args.grammar_dir)
        except Exception as exc:
            log(f"stopped at {spec.id}: {type(exc).__name__}; re-run the same command to resume")
            raise SystemExit(1)
    log("done")


if __name__ == "__main__":
    main()
