"""Render the system architecture / workflow diagram to PDF, PNG and SVG (matplotlib).

The figure is drawn at its printed size (7.16 in = IEEE two-column width) so that the
fonts stay readable when placed with \\begin{figure*} ... \\includegraphics[width=\\textwidth].
"""
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "figures"

W, H = 7.16, 3.0
INK = "#33414e"
EDGE = "#4a5866"
LOOP = "#a8641b"
PANELS = {  # x0, x1, fill, edge, title
    "A": (0.04, 1.14, "#eef3f8", "#9fb3c8", "1  Benchmark", "DTBench, 12 specifications"),
    "B": (1.24, 2.52, "#f1f6ec", "#a9bf8f", "2  LLM generation", "local open-weight LLMs, T = 0"),
    "C": (2.62, 3.90, "#fbf3e8", "#d9b98c", "3  Validation", "no ground truth needed"),
    "D": (4.00, 5.20, "#eef0f6", "#a3abc9", "4  Test derivation", "test suites per strategy"),
    "E": (5.30, 7.12, "#f4eef7", "#b9a2c6", "5  Evaluation", "against the ground truth"),
}


def panel(ax, key):
    x0, x1, fc, ec, title, sub = PANELS[key]
    ax.add_patch(FancyBboxPatch((x0, 0.06), x1 - x0, H - 0.12, boxstyle="round,pad=0,rounding_size=0.06",
                                fc=fc, ec=ec, lw=0.8))
    ax.text(x0 + 0.07, H - 0.18, title, fontsize=6.8, fontweight="bold", color=INK, va="center", ha="left")
    ax.text(x0 + 0.07, H - 0.33, sub, fontsize=5.3, color=INK, va="center", ha="left", style="italic")


def box(ax, x, y, w, h, title, sub="", fc="white", ec=EDGE, lw=0.8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.05", fc=fc, ec=ec, lw=lw))
    if sub:
        ax.text(x + w / 2, y + h * 0.66, title, fontsize=6.6, fontweight="bold", color=INK, ha="center", va="center")
        ax.text(x + w / 2, y + h * 0.30, sub, fontsize=5.5, color=INK, ha="center", va="center", linespacing=1.15)
    else:
        ax.text(x + w / 2, y + h / 2, title, fontsize=6.6, fontweight="bold", color=INK, ha="center", va="center")
    return {"l": (x, y + h / 2), "r": (x + w, y + h / 2), "t": (x + w / 2, y + h), "b": (x + w / 2, y),
            "x": x, "y": y, "w": w, "h": h}


def arrow(ax, p, q, label="", color=EDGE, ls="-", rad=0.0, lpos=0.5, loff=(0, 0.06), lw=0.9, ha="center"):
    a = FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=6.5, color=color, lw=lw, linestyle=ls,
                        connectionstyle=f"arc3,rad={rad}", shrinkA=1.5, shrinkB=1.5)
    ax.add_patch(a)
    if label:
        mx = p[0] + (q[0] - p[0]) * lpos + loff[0]
        my = p[1] + (q[1] - p[1]) * lpos + loff[1]
        ax.text(mx, my, label, fontsize=5.3, color=color, ha=ha, va="center", style="italic")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    for k in PANELS:
        panel(ax, k)

    # 1 input
    rules = box(ax, 0.10, 1.62, 0.98, 0.50, "Business rules", "natural-language\ntext")
    dd = box(ax, 0.10, 0.98, 0.98, 0.50, "Data dictionary", "inputs, domains,\noutput values")
    ax.text(0.59, 0.55, "sources:\ntextbook examples,\nGPT-DMN set,\nauthored rules", fontsize=5.3, color=INK,
            ha="center", va="center", linespacing=1.2)

    # 2 generation
    p0 = box(ax, 1.31, 2.04, 1.14, 0.48, "P0  Direct", "rules → test cases")
    p1 = box(ax, 1.31, 1.30, 1.14, 0.48, "P1  Table-first", "rules → decision table\n(JSON)")
    rep = box(ax, 1.31, 0.30, 1.14, 0.52, "P2  Repair", "table + reported issues\n→ corrected table (≤ 2×)")

    # 3 validation
    exe = box(ax, 2.69, 1.30, 1.14, 0.48, "Executable table", "safe AST predicates,\nT/F/- entries")
    prb = box(ax, 2.69, 0.78, 1.14, 0.42, "Probe synthesis", "boundaries, relations,\nrandom samples")
    chk = box(ax, 2.69, 0.24, 1.14, 0.44, "Structural check", "missed combinations,\nconflicts, bad syntax")

    # 4 tests
    der = box(ax, 4.06, 1.30, 1.08, 0.48, "Test derivation", "LLM: one test case\nper table rule")
    suites = box(ax, 4.06, 2.04, 1.08, 0.48, "Test suites", "P0 | P1 | P2")

    # 5 evaluation
    gt = box(ax, 5.37, 2.10, 1.50, 0.44, "Ground truth", "GT decision table + reference code",
             fc="#fbf9fc")
    sev = box(ax, 5.37, 1.36, 1.50, 0.56, "Test-suite assessment",
              "validity | oracle accuracy |\nrule coverage | missed combinations")
    mut = box(ax, 5.37, 0.80, 1.50, 0.40, "Mutation analysis", "324 non-equivalent mutants")
    tev = box(ax, 5.37, 0.22, 1.50, 0.44, "Table assessment", "accuracy | gaps | conflicts")

    # flow arrows
    arrow(ax, rules["r"], (p0["l"][0], p0["l"][1] - 0.06), rad=-0.15)
    arrow(ax, rules["r"], p1["l"])
    arrow(ax, (dd["r"][0], dd["r"][1] + 0.08), (p1["l"][0], p1["l"][1] - 0.12), rad=0.1)
    arrow(ax, p1["r"], exe["l"], "table", loff=(0, 0.07))
    arrow(ax, exe["b"], prb["t"])
    arrow(ax, prb["b"], chk["t"])
    arrow(ax, chk["l"], (rep["r"][0], chk["l"][1]), "issues", color=LOOP, ls="--", loff=(0.0, -0.07))
    arrow(ax, (rep["r"][0] - 0.12, rep["t"][1]), (exe["l"][0], exe["l"][1] - 0.14), "", color=LOOP,
          ls="--", rad=-0.3)
    ax.text(2.02, 1.05, "corrected\ntable", fontsize=5.3, color=LOOP, ha="center", va="center", style="italic")
    arrow(ax, exe["r"], der["l"], "P1", loff=(0, 0.07))
    arrow(ax, chk["r"], (der["b"][0] - 0.25, der["b"][1]), "", rad=0.25)
    ax.text(4.02, 0.83, "P2", fontsize=5.3, color=EDGE, ha="left", va="center", style="italic")
    arrow(ax, der["t"], suites["b"], "P1, P2", loff=(0.17, 0.0))
    arrow(ax, p0["r"], suites["l"], "P0 tests", lpos=0.5, loff=(0, 0.07))
    arrow(ax, suites["r"], sev["l"], rad=-0.2)
    arrow(ax, gt["b"], sev["t"])
    arrow(ax, sev["b"], mut["t"], "correct tests", loff=(0.27, 0.0))
    arrow(ax, (chk["r"][0], chk["r"][1] - 0.12), tev["l"], "tables (P1, P2)", lpos=0.5, loff=(0, -0.07))
    # ground truth bus on the right edge
    xb = 6.97
    ax.plot([gt["r"][0], xb, xb], [gt["r"][1], gt["r"][1], tev["r"][1]], color=EDGE, lw=0.8)
    for target in (mut, tev):
        arrow(ax, (xb, target["r"][1]), target["r"])

    for fmt in ("pdf", "svg", "png"):
        fig.savefig(OUT / f"architecture.{fmt}", dpi=300 if fmt == "png" else None)
    plt.close(fig)
    print("wrote figures/architecture.{pdf,svg,png}")


if __name__ == "__main__":
    main()
