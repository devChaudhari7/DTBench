"""Reinforcement-learning strategy P3: learn the decision table as a Q-table.

    python -m dtbench.rl.run          # trains on every (model, specification); settings in config/rl_config.json
"""
import gymnasium as gym

from .env import DecisionTableEnv
from .qlearning import QLearningAgent, learned_table, policy_accuracy, train

if "dtbench/DecisionTable-v0" not in gym.registry:
    gym.register(id="dtbench/DecisionTable-v0", entry_point="dtbench.rl.env:DecisionTableEnv")

__all__ = ["DecisionTableEnv", "QLearningAgent", "train", "learned_table", "policy_accuracy"]
