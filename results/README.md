# Results

* `raw/<model>/<spec>/` holds every prompt and raw model response:
  `P0_tests.json` (direct test generation), `P1_table.json` (decision table),
  `P2_repair1.json` / `P2_repair2.json` (repair rounds, only when the structural check found issues)
  and `P2_summary.json` (final P2 table and the issues reported in each round).
* `raw/<model>.log` is the run log (one line per LLM call with time, token counts and finish reason).
  `qwen3-4b.log` also records an aborted first session: at S05 the server slowed down and then ran out
  of memory with llama.cpp's default host prompt cache (a timeout, then refused connections). Failed calls
  are never stored; S05 to S12 were re-run with `--cache-ram 0` after the line `--- 04:21:41 ... resumed`.
  The repeated S05 table and repair calls produced exactly the same token counts as in the first session
  (greedy decoding). Only responses that completed are stored.
* `metrics_rows.csv|json`: all metrics for every (model, strategy, specification).
* `summary.csv|json`: totals and averages per (model, strategy).
* `stats.json`: paired Wilcoxon signed-rank tests over the 36 (model, specification) pairs.
* `benchmark_summary.csv|json`: size of every specification (inputs, conditions, rules, probes, mutants).
* `run_info.json`: llama.cpp builds and hardware.

`python scripts/make_results.py` regenerates every metric, table and figure from `raw/`.
