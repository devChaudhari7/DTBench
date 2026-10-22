"""Train the Q-learning agent (strategy P3) for every model and specification.

    python -m dtbench.rl.run [--models qwen3-4b,...] [--specs S01,...]

For each LLM, the conditions come from its validated decision table (P2, falling back to P1);
the run labelled "ground-truth" uses the ground-truth conditions (upper bound). Settings are read
from config/rl_config.json. Output per (model, spec) in results/rl/<model>/<spec>/:

    q_table.csv          the learned Q-table (one row per condition combination) and the decision
    learned_table.json   the greedy policy written as a decision table (used for test derivation)
    curve.csv            learning curve, one row per episode
    summary.json         sizes, final accuracy on the training inputs, run time
"""
import argparse
import json
import pathlib
import time

from ..specs import SPECS, SPEC_BY_ID
from .env import DecisionTableEnv
from .qlearning import QLearningAgent, learned_table, train, write_curve, write_json, write_q_table

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODELS = ["qwen3-4b", "llama3.2-3b", "gemma3-4b"]


def load_config(path=ROOT / "config" / "rl_config.json"):
    return json.loads(pathlib.Path(path).read_text())


def conditions_for(model, spec, raw_dir, source="P2"):
    """Conditions of the model's table; [] if the model produced no usable JSON table."""
    if model == "ground-truth":
        return spec.gt_table["conditions"]
    d = raw_dir / model / spec.id
    tables = []
    if source == "P2" and (d / "P2_summary.json").exists():
        tables.append(json.loads((d / "P2_summary.json").read_text()).get("final_table"))
    if (d / "P1_table.json").exists():
        tables.append(json.loads((d / "P1_table.json").read_text()).get("parsed"))
    for t in tables:
        if isinstance(t, dict) and isinstance(t.get("conditions"), list):
            return [c for c in t["conditions"] if isinstance(c, dict)]
    return []


def run_one(model, spec, cfg, raw_dir, out_dir):
    t0 = time.time()
    conds = conditions_for(model, spec, raw_dir, cfg.get("condition_source", "P2"))
    pool = cfg["pool"]
    env = DecisionTableEnv(spec.id, conds, pool_seed=pool["seed"], max_product=pool["max_product"],
                           n_relation=pool["n_relation"], n_random=pool["n_random"],
                           reward_correct=cfg["reward_correct"], reward_wrong=cfg["reward_wrong"])
    agent = QLearningAgent(int(env.observation_space.n), int(env.action_space.n), cfg["alpha"], cfg["gamma"], cfg["seed"])
    curve = train(env, agent, cfg["episodes"], cfg["epsilon_start"], cfg["epsilon_min"], cfg["epsilon_decay"],
                  cfg["seed"])
    d = out_dir / model / spec.id
    d.mkdir(parents=True, exist_ok=True)
    write_q_table(d / "q_table.csv", env, agent)
    write_json(d / "learned_table.json", learned_table(env, agent))
    write_curve(d / "curve.csv", curve)
    summary = {"model": model, "spec": spec.id, "conditions": len(env.condition_ids),
               "states": int(env.observation_space.n), "actions": int(env.action_space.n),
               "training_inputs": int(env.counts.sum()), "episodes": cfg["episodes"],
               "steps": sum(c["steps"] for c in curve), "final_policy_accuracy": curve[-1]["policy_accuracy"],
               "final_epsilon": curve[-1]["epsilon"], "seconds": round(time.time() - t0, 2)}
    write_json(d / "summary.json", summary)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(MODELS + ["ground-truth"]))
    ap.add_argument("--specs", default="all")
    ap.add_argument("--config", default=str(ROOT / "config" / "rl_config.json"))
    ap.add_argument("--raw", default=str(ROOT / "results" / "raw"))
    ap.add_argument("--out", default=str(ROOT / "results" / "rl"))
    a = ap.parse_args()
    cfg = load_config(a.config)
    specs = SPECS if a.specs == "all" else [SPEC_BY_ID[s] for s in a.specs.split(",")]
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "config_used.json", cfg)
    for model in a.models.split(","):
        for spec in specs:
            s = run_one(model, spec, cfg, pathlib.Path(a.raw), out)
            print(f"{model:13s} {spec.id}  conditions={s['conditions']:2d} states={s['states']:4d} "
                  f"actions={s['actions']} steps={s['steps']:6d} accuracy={100 * s['final_policy_accuracy']:5.1f}% "
                  f"({s['seconds']}s)", flush=True)


if __name__ == "__main__":
    main()
