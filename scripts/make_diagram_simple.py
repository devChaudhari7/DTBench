"""Simple, plain-language version of the architecture diagram (figures/architecture_simple.png/pdf)."""
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = pathlib.Path(__file__).resolve().parents[1] / "figures"
INK, MUTED = "#1f2328", "#57606a"
BLUE, ORANGE, GREEN, YELLOW, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8c959f"

fig, ax = plt.subplots(figsize=(13, 7.2))
ax.set_xlim(0, 13)
ax.set_ylim(0, 7.2)
ax.axis("off")


def box(x, y, w, h, num, title, lines, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.18",
                                fc=color + "1f", ec=color, lw=2))
    ax.add_patch(plt.Circle((x + 0.38, y + h - 0.38), 0.24, color=color))
    ax.text(x + 0.38, y + h - 0.38, num, ha="center", va="center", color="white", fontsize=12, weight="bold")
    ax.text(x + 0.75, y + h - 0.38, title, ha="left", va="center", color=INK, fontsize=13, weight="bold")
    ax.text(x + 0.25, y + h - 0.85, "\n".join(lines), ha="left", va="top", color=INK, fontsize=10.5,
            linespacing=1.45)


def arrow(p, q, label=None, color=INK, rad=0.0, lx=0, ly=0.18):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=18, lw=1.8, color=color,
                                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        ax.text((p[0] + q[0]) / 2 + lx, (p[1] + q[1]) / 2 + ly, label, ha="center", va="bottom",
                fontsize=9.5, color=color, style="italic")


ax.text(6.5, 6.95, "How the project works (simple view)", ha="center", va="center", fontsize=16,
        weight="bold", color=INK)

# top row
box(0.2, 4.0, 3.6, 2.45, "1", "Business rules", [
    "Rules written in plain English,", "e.g. \"block a UPI transfer", "above Rs 1,00,000\"",
    "(12 rule sets in our dataset)"], GREY)
box(4.7, 4.0, 3.6, 2.45, "2", "AI writes the table", [
    "A small AI model (LLM) reads", "the rules and writes a", "decision table:",
    "conditions + rules (T / F / -)"], BLUE)
box(9.2, 4.0, 3.6, 2.45, "3", "Checker finds mistakes", [
    "Tries many inputs and finds", "- missing cases (no rule fits)", "- conflicts (two rules disagree)",
    "Sends them back to the AI to fix"], ORANGE)

# bottom row
box(9.2, 0.35, 3.6, 2.6, "4", "Q-learning (RL)", [
    "Gym environment: for each", "combination it guesses an output,", "gets +1 if right, -1 if wrong.",
    "After 150 episodes the Q-table", "becomes the final decision table"], GREEN)
box(4.7, 0.35, 3.6, 2.6, "5", "Make test cases", [
    "One test case for each rule", "of the table:", "input values + expected output",
    "(we also compare with tests", "the AI writes directly)"], YELLOW)
box(0.2, 0.35, 3.6, 2.6, "6", "Score the results", [
    "Compare with the correct answers:", "- rule coverage (rules tested)", "- mutation score (bugs caught)",
    "- table accuracy"], GREY)

arrow((3.85, 5.2), (4.65, 5.2))
arrow((8.35, 5.55), (9.15, 5.55))
# repair loop 3 -> 2
arrow((9.15, 4.75), (8.35, 4.75), None, ORANGE)
ax.text(8.75, 4.62, "fix it\n(max 2x)", ha="center", va="top", fontsize=9.5, color=ORANGE, style="italic")
arrow((11.0, 3.95), (11.0, 3.0), None)
ax.text(11.12, 3.47, "keep the conditions,\nlearn the outputs", fontsize=9.5, color=GREEN, style="italic",
        va="center")
arrow((9.15, 1.65), (8.35, 1.65), "Q-table", GREEN, ly=0.12)
arrow((4.65, 1.65), (3.85, 1.65), "tests", INK, ly=0.12)

for ext in ("png", "pdf"):
    fig.savefig(OUT / f"architecture_simple.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
print("wrote", OUT / "architecture_simple.png")
