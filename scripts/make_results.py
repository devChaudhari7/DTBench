"""Aggregate metrics, run significance tests, and write LaTeX tables + figures.

    python scripts/make_results.py          # after the experiment (uses results/raw)
"""
import collections
import json
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402
from scipy.stats import wilcoxon        # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dtbench.analysis import MODEL_NAMES, STRATEGY_NAMES, run   # noqa: E402
from dtbench.specs import SPECS                                    # noqa: E402

RES, FIG, TAB = ROOT / "results", ROOT / "figures", ROOT / "tables"

# palette (validated categorical slots 1-4 for strategies, 5-7 for models in the RL figure) and chart ink
COL = {"P0": "#2a78d6", "P1": "#eb6834", "P2": "#1baf7a", "P3": "#eda100"}
MODEL_COL = {"qwen3-4b": "#e87ba4", "llama3.2-3b": "#008300", "gemma3-4b": "#6250d6"}
STRATS = ("P0", "P1", "P2", "P3")
SHORT = {"S01": "Triangle", "S02": "NextDate", "S03": "Order discount", "S04": "BMI level", "S05": "Pet adoption",
         "S06": "Driver's licence", "S07": "Vacation days", "S08": "Transport mode", "S09": "Scholarship",
         "S10": "Login + OTP", "S11": "UPI transfer", "S12": "Personal loan"}
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUES = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6",
         "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.edgecolor": AXIS,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
                     "xtick.major.size": 2.5, "ytick.major.size": 2.5, "legend.frameon": False})


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def pct(x, nd=1):
    return "--" if x is None else f"{100 * x:.{nd}f}"


def two_line(model):
    """'Llama-3.2-3B' -> 'Llama-3.2\\n3B' so neighbouring labels never collide."""
    name = MODEL_NAMES.get(model, model)
    head, _, size = name.rpartition("-")
    return f"{head}\n{size}" if head else name


def aggregate(rows):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["model"], r["strategy"])].append(r)
    out = []
    for (model, strat), rs in groups.items():
        live = sum(r["mutants"] for r in rs)
        rules_total = sum(len(s.feasible_gt_rules()) for s in SPECS if s.id in {r["spec"] for r in rs})
        a = {"model": model, "strategy": strat, "specs": len(rs),
             "tests_mean": mean([r["n_tests"] for r in rs]),
             "tests_total": sum(r["n_tests"] for r in rs),
             "validity": mean([r["validity"] for r in rs if r["n_tests"]]),
             "oracle_accuracy": mean([r["oracle_accuracy"] for r in rs if r["n_valid"]]),
             "rule_coverage_macro": mean([r["rule_coverage"] for r in rs]),
             "rules_covered": rules_total - sum(r["n_missed"] for r in rs),
             "rules_total": rules_total,
             "rule_coverage_pooled": (rules_total - sum(r["n_missed"] for r in rs)) / rules_total,
             "missed_total": sum(r["n_missed"] for r in rs),
             "mutation_score_macro": mean([r["mutation_score"] for r in rs]),
             "killed": sum(r["killed"] for r in rs), "live_mutants": live,
             "mutation_score_pooled": sum(r["killed"] for r in rs) / live if live else None,
             "llm_calls": sum(r.get("llm_calls", 0) for r in rs),
             "llm_seconds": sum(r.get("llm_seconds", 0) for r in rs),
             "completion_tokens": sum(r.get("completion_tokens", 0) for r in rs),
             "json_ok": sum(1 for r in rs if r.get("json_ok", True))}
        if strat in ("P1", "P2", "P3"):
            us = [r for r in rs if r.get("table_usable")]
            a.update({"tables_usable": len(us),
                      "tables_clean": sum(1 for r in us if r.get("sc_clean")),
                      "table_accuracy": mean([r.get("probe_accuracy", 0.0) if r.get("table_usable") else 0.0
                                              for r in rs]),
                      "gap_rate": mean([r["probe_gap_rate"] for r in us]),
                      "conflict_rate": mean([r["probe_conflict_rate"] for r in us]),
                      "rule_correctness": mean([r.get("rule_correctness", 0.0) if r.get("table_usable") else 0.0
                                                for r in rs]),
                      "gt_rules_with_gap": sum(len(r.get("rules_with_gap", [])) for r in us),
                      "gt_rules_with_conflict": sum(len(r.get("rules_with_conflict", [])) for r in us),
                      "gt_rules_wrong": sum(len(r.get("rules_with_wrong_output", [])) for r in us),
                      "first_hit_accuracy": mean([r.get("first_hit_accuracy") for r in us])})
        if strat == "P2":
            a.update({"tables_changed": sum(1 for r in rs if r.get("table_changed")),
                      "repair_calls": sum(r.get("repair_rounds", 0) for r in rs)})
        if strat == "P3":
            a.update({"rl_states": sum(r.get("rl_states") or 0 for r in rs),
                      "rl_steps": sum(r.get("rl_steps") or 0 for r in rs),
                      "rl_seconds": round(sum(r.get("rl_seconds") or 0 for r in rs), 2),
                      "rl_train_accuracy": mean([r.get("rl_train_accuracy") for r in rs])})
        out.append(a)
    order = {m: i for i, m in enumerate(list(MODEL_NAMES) + ["ground-truth"])}
    out.sort(key=lambda a: (order.get(a["model"], 99), a["strategy"]))
    return out


def paired(rows, metric, s1, s2):
    """Wilcoxon signed-rank over (model, spec) pairs: s2 versus s1."""
    by = {(r["model"], r["spec"], r["strategy"]): r for r in rows if r["model"] != "ground-truth"}
    xs, ys = [], []
    for (m, sp, st), r in by.items():
        if st == s1 and (m, sp, s2) in by:
            x, y = r.get(metric), by[(m, sp, s2)].get(metric)
            if x is not None and y is not None:
                xs.append(x)
                ys.append(y)
    d = np.array(ys) - np.array(xs)
    res = {"metric": metric, "comparison": f"{s2} vs {s1}", "n": len(d),
           "better": int((d > 1e-12).sum()), "worse": int((d < -1e-12).sum()),
           "ties": int((np.abs(d) <= 1e-12).sum()),
           "mean_diff": float(d.mean()) if len(d) else None,
           "median_diff": float(np.median(d)) if len(d) else None}
    nz = d[np.abs(d) > 1e-12]
    if len(nz) >= 1:
        stat = wilcoxon(nz, zero_method="wilcox", alternative="two-sided")
        res["W"] = float(stat.statistic)
        res["p"] = float(stat.pvalue)
        from scipy.stats import rankdata
        ranks = rankdata(np.abs(nz))
        pos = float(ranks[nz > 0].sum())
        tot = len(nz) * (len(nz) + 1) / 2
        res["rank_biserial"] = float((pos - (tot - pos)) / tot)
    return res


# ------------------------------------------------------------------------------------------------
def fig_coverage(agg, models):
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.15), gridspec_kw={"wspace": 0.22})
    ref = {a["strategy"]: a for a in agg if a["model"] == "ground-truth"}["REF"]
    panels = [("rule_coverage_pooled", "Rule coverage (%)", 1.0, "ground-truth table: 100%"),
              ("mutation_score_pooled", "Mutation score (%)", ref["mutation_score_pooled"],
               f"ground-truth table: {100 * ref['mutation_score_pooled']:.0f}%")]
    look = {(a["model"], a["strategy"]): a for a in agg}
    for ax, (key, label, refv, reftxt) in zip(axes, panels):
        x = np.arange(len(models))
        w = 0.18
        for i, s in enumerate(STRATS):
            vals = [100 * (look.get((m, s), {}).get(key) or 0) for m in models]
            ax.bar(x + (i - 1.5) * (w + 0.025), vals, width=w, color=COL[s], label=f"{s} {STRATEGY_NAMES[s]}",
                   zorder=3)
        ax.axhline(100 * refv, color=MUTED, lw=0.9, ls=(0, (4, 2)), zorder=2,
                   label="Ground-truth table (reference suite)")
        ax.set_xticks(x)
        ax.set_xticklabels([MODEL_NAMES.get(m, m) for m in models], color=INK)
        ax.set_ylim(0, 112)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_ylabel(label)
        ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.set_xlim(-0.6, len(models) - 0.4)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=5, fontsize=6.3, bbox_to_anchor=(0.5, 1.02),
               handlelength=1.3, columnspacing=1.1)
    fig.subplots_adjust(top=0.84, bottom=0.12, left=0.07, right=0.99)
    for fmt in ("pdf", "png"):
        fig.savefig(FIG / f"fig_coverage_mutation.{fmt}", dpi=300)
    plt.close(fig)


def fig_heatmap(rows, models):
    cols = [(m, s) for m in models for s in STRATS]
    look = {(r["model"], r["strategy"], r["spec"]): r for r in rows}
    data = np.full((len(SPECS), len(cols)), np.nan)
    for i, sp in enumerate(SPECS):
        for j, (m, s) in enumerate(cols):
            r = look.get((m, s, sp.id))
            if r:
                data[i, j] = 100 * r["rule_coverage"]
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("blues", BLUES)
    fig, ax = plt.subplots(figsize=(3.5, 3.55))
    im = ax.imshow(data, cmap=cmap, vmin=0, vmax=100, aspect="auto")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            if np.isnan(v):
                continue
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=4.9,
                    color="white" if v >= 62 else INK)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([s for _, s in cols], fontsize=5.4)
    ax.set_yticks(range(len(SPECS)))
    ax.set_yticklabels([f"{s.id} {SHORT.get(s.id, s.name)}" for s in SPECS], fontsize=6.0, color=INK)
    k_per = len(STRATS)
    for k, m in enumerate(models):
        ax.text(k_per * k + (k_per - 1) / 2, -0.72, two_line(m), ha="center", va="bottom",
                fontsize=6.0, color=INK, linespacing=1.05)
        if k:
            ax.axvline(k_per * k - 0.5, color="white", lw=2.0)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.subplots_adjust(left=0.27, right=0.87, top=0.88, bottom=0.07)
    pos = ax.get_position()
    cax = fig.add_axes([pos.x1 + 0.016, pos.y0, 0.018, pos.height])
    cb = fig.colorbar(im, cax=cax)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=6, length=0)
    cb.set_label("rule coverage (%)", fontsize=6.0, color=INK2, labelpad=2)
    for fmt in ("pdf", "png"):
        fig.savefig(FIG / f"fig_heatmap_rule_coverage.{fmt}", dpi=300)
    plt.close(fig)


def fig_validation(agg, models):
    look = {(a["model"], a["strategy"]): a for a in agg}
    panels = [("tables_clean", "Tables with no\nstructural issue (of 12)", 1, 12),
              ("table_accuracy", "Table accuracy on\nevaluation probes (%)", 100, 100),
              ("gt_rules_with_gap", "Ground-truth rules with a\nmissing combination", 1, None)]
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.1), gridspec_kw={"wspace": 0.38})
    for ax, (key, label, scale, ymax) in zip(axes, panels):
        x = np.arange(len(models))
        w = 0.3
        for i, s in enumerate(("P1", "P2")):
            vals = [scale * (look.get((m, s), {}).get(key) or 0) for m in models]
            xs = x + (i - 0.5) * (w + 0.04)
            ax.bar(xs, vals, width=w, color=COL[s], zorder=3, label=f"{s} {STRATEGY_NAMES[s]}")
            for xv, v in zip(xs, vals):           # a zero bar is invisible: say so explicitly
                if abs(v) < 1e-9:
                    ax.text(xv, 0, "0", ha="center", va="bottom", fontsize=5.6, color=INK2, zorder=4)
        ax.set_xticks(x)
        ax.set_xticklabels([two_line(m) for m in models], fontsize=6.4, color=INK, linespacing=1.05)
        ax.set_title(label, fontsize=7, color=INK, pad=4)
        if ymax:
            ax.set_ylim(0, ymax * 1.05)
        else:
            top = max([scale * (look.get((m, s), {}).get(key) or 0) for m in models for s in ("P1", "P2")] + [1])
            ax.set_ylim(0, top * 1.15 + 0.5)
            ax.yaxis.get_major_locator().set_params(integer=True)
        ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=2, fontsize=7, bbox_to_anchor=(0.5, 1.03), handlelength=1.0)
    fig.subplots_adjust(top=0.73, bottom=0.17, left=0.05, right=0.99)
    for fmt in ("pdf", "png"):
        fig.savefig(FIG / f"fig_validation_repair.{fmt}", dpi=300)
    plt.close(fig)


def fig_rl_learning(models):
    """Mean greedy-policy accuracy on the training inputs per episode (average over the 12 specifications)."""
    import csv as _csv
    series = [(m, MODEL_NAMES.get(m, m), MODEL_COL.get(m, INK2), "-") for m in models]
    series.append(("ground-truth", "Ground-truth conditions", INK, (0, (4, 2))))
    fig, ax = plt.subplots(figsize=(3.5, 2.25))
    last = 1
    for key, label, color, ls in series:
        curves = []
        for sp in SPECS:
            f = RES / "rl" / key / sp.id / "curve.csv"
            if f.exists():
                curves.append([float(r["policy_accuracy"]) for r in _csv.DictReader(open(f))])
        if not curves:
            continue
        n = min(len(c) for c in curves)
        y = 100 * np.mean([c[:n] for c in curves], axis=0)
        x = np.arange(1, n + 1)
        last = max(last, n)
        is_gt = key == "ground-truth"
        ax.plot(x, y, color=color, lw=1.0 if is_gt else 1.6, ls=ls, label=label, zorder=4 if is_gt else 3)
    ax.legend(loc="lower right", fontsize=6.2, handlelength=2.2, borderaxespad=0.6)
    ax.set_xlim(1, last)
    ax.set_ylim(40, 102)
    ax.set_xticks([1, 25, 50, 75, 100, 125, 150])
    ax.set_xlabel("Training episode (epoch)")
    ax.set_ylabel("Policy accuracy (%)")
    ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.subplots_adjust(left=0.14, right=0.97, top=0.96, bottom=0.18)
    for fmt in ("pdf", "png"):
        fig.savefig(FIG / f"fig_rl_learning.{fmt}", dpi=300)
    plt.close(fig)


# ------------------------------------------------------------------------------------------------
def tex_escape(s):
    return str(s).replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#")


def tab_benchmark(bench):
    lines = [r"\begin{table}[t]", r"\centering",
             r"\caption{DTBench specifications.}", r"\label{tab:benchmark}",
             r"\footnotesize", r"\setlength{\tabcolsep}{3.2pt}",
             r"\begin{tabular}{@{}llrrrr@{}}", r"\toprule",
             r"ID & Specification (source) & In & Cond & Rules & Mut \\", r"\midrule"]
    src = {"Textbook": "textbook", "GPT-DMN": "GPT-DMN", "Business rules (authored)": "authored"}
    for b in bench:
        lines.append(f"{b['spec']} & {tex_escape(b['name'])} ({src.get(b['category'], b['category'])}) & "
                     f"{b['inputs']} & {b['gt_conditions']} & {b['gt_rules']} & {b['live_mutants']} \\\\")
    lines += [r"\midrule",
              f"\\multicolumn{{2}}{{@{{}}l}}{{Total}} & {sum(b['inputs'] for b in bench)} & "
              f"{sum(b['gt_conditions'] for b in bench)} & {sum(b['gt_rules'] for b in bench)} & "
              f"{sum(b['live_mutants'] for b in bench)} \\\\",
              r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (TAB / "tab_benchmark.tex").write_text("\n".join(lines) + "\n")


def tab_main(agg, models):
    look = {(a["model"], a["strategy"]): a for a in agg}
    lines = [r"\begin{table*}[t]", r"\centering",
             r"\caption{Test-suite results per model and strategy.}",
             r"\label{tab:main}", r"\small",
             r"\begin{tabular}{@{}llrrrrrr@{}}", r"\toprule",
             r"Model & Strategy & Tests & Valid (\%) & Oracle acc. (\%) & Rule cov. (\%) & Missed rules & "
             r"Mutation score (\%) \\", r"\midrule"]
    for m in models:
        for i, s in enumerate(STRATS):
            a = look.get((m, s))
            if not a:
                continue
            name = MODEL_NAMES.get(m, m) if i == 0 else ""
            lines.append(f"{name} & {s} {STRATEGY_NAMES[s]} & {a['tests_total']} & {pct(a['validity'])} & "
                         f"{pct(a['oracle_accuracy'])} & {pct(a['rule_coverage_pooled'])} & "
                         f"{a['missed_total']} & {pct(a['mutation_score_pooled'])} \\\\")
        lines.append(r"\addlinespace")
    for key, name, desc in ((("ground-truth", "P3"), "GT conditions", "P3 Q-learning (RL)"),
                            (("ground-truth", "REF"), "GT reference", "one test per GT rule")):
        ref = look.get(key)
        if ref:
            lines.append(f"{name} & {desc} & {ref['tests_total']} & {pct(ref['validity'])} & "
                         f"{pct(ref['oracle_accuracy'])} & {pct(ref['rule_coverage_pooled'])} & {ref['missed_total']} & "
                         f"{pct(ref['mutation_score_pooled'])} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    (TAB / "tab_main_results.tex").write_text("\n".join(lines) + "\n")


def tab_tables(agg, models):
    look = {(a["model"], a["strategy"]): a for a in agg}
    lines = [r"\begin{table}[t]", r"\centering",
             r"\caption{Decision-table quality: the LLM's table (P1), after repair (P2) and learned by Q-learning on "
             r"the LLM's conditions (P3); Acc., Gap, Confl.\ and Correct in \%.}",
             r"\label{tab:tables}", r"\footnotesize", r"\setlength{\tabcolsep}{3.4pt}",
             r"\begin{tabular}{@{}llrrrrrr@{}}", r"\toprule",
             r"Model & & Usable & Clean & Acc. & Gap & Confl. & Correct \\", r"\midrule"]
    for m in models:
        for i, s in enumerate(("P1", "P2", "P3")):
            a = look.get((m, s))
            if not a:
                continue
            name = MODEL_NAMES.get(m, m) if i == 0 else ""
            lines.append(f"{name} & {s} & {a['tables_usable']}/12 & {a['tables_clean']}/12 & "
                         f"{pct(a['table_accuracy'])} & {pct(a['gap_rate'])} & {pct(a['conflict_rate'])} & "
                         f"{pct(a['rule_correctness'])} \\\\")
    a = look.get(("ground-truth", "P3"))
    if a:
        lines.append(r"\addlinespace")
        lines.append(f"GT cond. & P3 & {a['tables_usable']}/12 & {a['tables_clean']}/12 & "
                     f"{pct(a['table_accuracy'])} & {pct(a['gap_rate'])} & {pct(a['conflict_rate'])} & "
                     f"{pct(a['rule_correctness'])} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (TAB / "tab_table_quality.tex").write_text("\n".join(lines) + "\n")


def main():
    for d in (FIG, TAB):
        d.mkdir(parents=True, exist_ok=True)
    rows, bench = run()
    models = [m for m in MODEL_NAMES if any(r["model"] == m for r in rows)]
    agg = aggregate(rows)
    (RES / "summary.json").write_text(json.dumps(agg, indent=1))
    from dtbench.analysis import write_csv
    write_csv(RES / "summary.csv", agg)
    stats = []
    for metric in ("rule_coverage", "mutation_score", "oracle_accuracy"):
        for s1, s2 in (("P0", "P1"), ("P1", "P2"), ("P0", "P2"), ("P2", "P3"), ("P0", "P3")):
            stats.append(paired(rows, metric, s1, s2))
    for s1, s2 in (("P1", "P2"), ("P2", "P3"), ("P1", "P3")):
        stats.append(paired(rows, "probe_accuracy", s1, s2))
        stats.append(paired(rows, "rule_correctness", s1, s2))
    (RES / "stats.json").write_text(json.dumps(stats, indent=1))
    tab_benchmark(bench)
    if models:
        tab_main(agg, models)
        tab_tables(agg, models)
        fig_coverage(agg, models)
        fig_heatmap(rows, models)
        fig_validation(agg, models)
        fig_rl_learning(models)
    print("models:", models)
    for a in agg:
        print(f"{a['model']:12s} {a['strategy']:3s} specs={a['specs']:2d} tests={a['tests_total']:4d} "
              f"oracle={pct(a['oracle_accuracy'])} RC={pct(a['rule_coverage_pooled'])} missed={a['missed_total']:3d} "
              f"MS={pct(a['mutation_score_pooled'])}"
              + (f" tbl_acc={pct(a.get('table_accuracy'))} clean={a.get('tables_clean')}" if 'table_accuracy' in a else ""))
    for s in stats:
        print(f"{s['metric']:16s} {s['comparison']:9s} n={s['n']:2d} +{s['better']} -{s['worse']} ={s['ties']} "
              f"mean_diff={s['mean_diff'] if s['mean_diff'] is None else round(s['mean_diff'], 3)} p={s.get('p')}")


if __name__ == "__main__":
    main()
