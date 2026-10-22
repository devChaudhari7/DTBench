"""Gymnasium environment in which an agent learns a decision table as a Q-table.

The conditions of a decision table (written by the LLM, or the ground-truth conditions) split
the input space into condition combinations. In every step the environment shows one test input:

* observation: the index of the condition combination the input falls in (the state);
* action:      the index of the output value the agent chooses for it;
* reward:      +1 if that output equals the output of the system under test, -1 otherwise.

One episode shows every known condition combination once, in random order, each time with a
random input from that combination; an episode is therefore one pass (epoch) over the table.
The system under test is the specification's reference implementation.

    import gymnasium as gym, dtbench.rl
    env = gym.make("dtbench/DecisionTable-v0", spec_id="S11", conditions=[{"id": "C1", "expr": "amount > 100000"}])
"""
import collections

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from ..expr import parse_expr
from ..probes import synthesize
from ..specs import SPEC_BY_ID
from ..table import DecisionTable


def combination_text(vector):
    """(True, False, None) -> 'TF?'."""
    return "".join("T" if v is True else "F" if v is False else "?" for v in vector)


class DecisionTableEnv(gym.Env):
    metadata = {"render_modes": ["ansi"], "render_fps": 4}

    def __init__(self, spec_id, conditions, pool_seed=7, max_product=3000, n_relation=50, n_random=2000,
                 reward_correct=1.0, reward_wrong=-1.0, render_mode=None):
        self.spec = SPEC_BY_ID[spec_id]
        self.table = DecisionTable({"conditions": list(conditions or []), "rules": []}, self.spec)
        self.condition_ids = list(self.table.condition_order)
        self.condition_texts = [self.table.conditions[c].text for c in self.condition_ids]

        # training inputs: built from the table's own conditions (no ground truth involved)
        trees = [c.tree for c in self.table.conditions.values()]
        if self.spec.constraint:
            trees.append(parse_expr(self.spec.constraint, self.spec.var_names))
        pool = synthesize(self.spec, trees, seed=pool_seed, max_product=max_product,
                          n_relation=n_relation, n_random=n_random)
        groups = collections.OrderedDict()
        for x in pool:
            groups.setdefault(self.table.condition_vector(x), []).append(x)
        self.states = list(groups)                        # one state per condition combination
        self.inputs = [groups[v] for v in self.states]

        # the system under test answers every training input once (its outputs give the rewards)
        truth = [[self.spec.reference_output(x) for x in xs] for xs in self.inputs]
        if self.spec.output_type == "int":                # no fixed label set: use the outputs observed
            self.actions = sorted({o for t in truth for o in t}, key=int)
        else:
            self.actions = list(self.spec.output_values)
        index = {a: i for i, a in enumerate(self.actions)}
        self.answers = [np.array([index[o] for o in t], dtype=np.int64) for t in truth]
        self.counts = np.zeros((len(self.states), len(self.actions)), dtype=np.int64)
        for s, ans in enumerate(self.answers):
            np.add.at(self.counts[s], ans, 1)

        self.observation_space = spaces.Discrete(len(self.states))
        self.action_space = spaces.Discrete(len(self.actions))
        self.reward_correct, self.reward_wrong = float(reward_correct), float(reward_wrong)
        self.render_mode = render_mode
        self._order, self._t, self._current = None, 0, (0, 0)

    # ------------------------------------------------------------------------------------------
    def _show(self, state):
        i = int(self.np_random.integers(len(self.inputs[state])))
        self._current = (int(state), i)
        return int(state)

    def _info(self):
        s, i = self._current
        return {"input": self.inputs[s][i], "combination": combination_text(self.states[s])}

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._order = self.np_random.permutation(len(self.states))
        self._t = 0
        return self._show(self._order[0]), self._info()

    def step(self, action):
        s, i = self._current
        correct = int(self.answers[s][i])
        reward = self.reward_correct if int(action) == correct else self.reward_wrong
        info = {**self._info(), "chosen_output": self.actions[int(action)], "system_output": self.actions[correct]}
        self._t += 1
        terminated = self._t >= len(self.states)
        obs = s if terminated else self._show(self._order[self._t])
        return obs, reward, terminated, False, info

    def render(self):
        if self.render_mode == "ansi":
            s, i = self._current
            return f"state {s} [{combination_text(self.states[s])}] input {self.inputs[s][i]}"
        return None
