"""Tabular Q-learning agent and helpers that turn the learned Q-table into a decision table.

Update rule (Watkins' Q-learning):

    Q(s, a) <- Q(s, a) + alpha * (r + gamma * max_a' Q(s', a') - Q(s, a))

With gamma = 0 (the next input does not depend on the agent's answer) the update is a running
average of the rewards, so Q(s, a) approaches 2p - 1, where p is the share of inputs in
combination s for which the system outputs a; the greedy policy picks the most frequent output.
"""
import csv
import json

import numpy as np


class QLearningAgent:
    def __init__(self, n_states, n_actions, alpha=0.1, gamma=0.0, seed=0):
        self.q = np.zeros((n_states, n_actions))
        self.visits = np.zeros((n_states, n_actions), dtype=np.int64)
        self.alpha, self.gamma = float(alpha), float(gamma)
        self.rng = np.random.default_rng(seed)

    def act(self, state, epsilon):
        """Epsilon-greedy action; ties between equal Q-values are broken at random."""
        if self.rng.random() < epsilon:
            return int(self.rng.integers(self.q.shape[1]))
        row = self.q[state]
        return int(self.rng.choice(np.flatnonzero(row == row.max())))

    def update(self, state, action, reward, next_state, done):
        target = reward if (done or self.gamma == 0.0) else reward + self.gamma * self.q[next_state].max()
        self.q[state, action] += self.alpha * (target - self.q[state, action])
        self.visits[state, action] += 1

    def greedy(self):
        return self.q.argmax(axis=1)


def policy_accuracy(env, agent):
    """Share of the environment's inputs for which the greedy action equals the system's output."""
    pol = agent.greedy()
    return float(env.counts[np.arange(len(pol)), pol].sum() / env.counts.sum())


def train(env, agent, episodes, epsilon_start=1.0, epsilon_min=0.05, epsilon_decay=0.97, seed=0):
    """Run the episodes; returns one learning-curve row per episode."""
    curve, eps = [], float(epsilon_start)
    for ep in range(episodes):
        obs, _ = env.reset(seed=seed + ep)
        total = steps = correct = 0
        done = False
        while not done:
            action = agent.act(obs, eps)
            nxt, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            agent.update(obs, action, reward, nxt, done)
            total += reward
            steps += 1
            correct += reward > 0
            obs = nxt
        curve.append({"episode": ep + 1, "epsilon": round(eps, 4), "steps": steps,
                      "mean_reward": round(total / steps, 4), "train_accuracy": round(correct / steps, 4),
                      "policy_accuracy": round(policy_accuracy(env, agent), 4)})
        eps = max(float(epsilon_min), eps * float(epsilon_decay))
    return curve


def learned_table(env, agent):
    """The greedy policy as a decision table: one rule per visited condition combination."""
    rules = []
    pol = agent.greedy()
    for s, vec in enumerate(env.states):
        if any(v is None for v in vec) or agent.visits[s].sum() == 0:
            continue                                    # cannot be written as T/F entries / never seen
        rules.append({"id": f"R{len(rules) + 1}", "when": dict(zip(env.condition_ids, vec)),
                      "output": env.actions[int(pol[s])]})
    return {"conditions": [{"id": c, "expr": t} for c, t in zip(env.condition_ids, env.condition_texts)],
            "rules": rules}


def write_q_table(path, env, agent):
    """CSV: one row per state (condition combination), one Q-value column per output, the decision."""
    pol = agent.greedy()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["state"] + [f"{c}: {t}" for c, t in zip(env.condition_ids, env.condition_texts)]
                   + [f"Q[{a}]" for a in env.actions] + ["visits", "inputs", "decision"])
        for s, vec in enumerate(env.states):
            w.writerow([s] + ["T" if v is True else "F" if v is False else "?" for v in vec]
                       + [f"{q:.4f}" for q in agent.q[s]]
                       + [int(agent.visits[s].sum()), len(env.inputs[s]), env.actions[int(pol[s])]])


def write_curve(path, curve):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(curve[0]))
        w.writeheader()
        w.writerows(curve)


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False))
