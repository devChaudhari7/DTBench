# Configuration (properties) files

Both files are read by the code; change a value here instead of in the code.

## `llm_config.json` - LLM strategies P0, P1, P2 (read by `dtbench/runner.py`)

| Key | Value | Meaning |
|---|---|---|
| `temperature` | 0.0 | greedy decoding: the same prompt always gives the same answer |
| `seed` | 42 | random seed sent with every request |
| `max_tokens` | 2500 | longest answer the model may write in one call |
| `max_repair_rounds` | 2 | P2: at most two repair calls per specification |
| `max_issues_per_repair` | 6 | P2: at most six problems (with example inputs) sent in one repair prompt |

The models are used as they are (pre-trained, 4-bit GGUF); there is no training and therefore no epochs.
Server settings (context 6144 tokens, one slot, no prompt cache) are in `scripts/run_model.sh` and
`scripts/run_models_windows.ps1`.

## `rl_config.json` - Q-learning strategy P3 (read by `dtbench/rl/run.py`)

| Key | Value | Meaning |
|---|---|---|
| `episodes` | 150 | training episodes (epochs); one episode shows every condition combination once |
| `alpha` | 0.1 | learning rate of the Q-table update |
| `gamma` | 0.0 | discount factor; 0 because the next input does not depend on the agent's answer |
| `epsilon_start`, `epsilon_min`, `epsilon_decay` | 1.0, 0.05, 0.97 | epsilon-greedy exploration, multiplied by the decay after every episode |
| `reward_correct`, `reward_wrong` | +1, -1 | reward when the chosen output matches / does not match the system's output |
| `seed` | 42 | seed for the environment and the agent |
| `condition_source` | `P2` | conditions come from the LLM's validated table (P2); the ground-truth conditions are used for the upper-bound run |
| `pool` | seed 7, 3000 / 50 / 2000 | training inputs: predicate-guided combinations, relation probes, uniform random inputs |
