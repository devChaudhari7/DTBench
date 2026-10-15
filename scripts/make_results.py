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

# palette (validated categorical slots 1-3) and chart ink
COL = {"P0": "#2a78d6", "P1": "#eb6834", "P2": "#1baf7a"}
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
        if strat in ("P1", "P2"):
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
        w = 0.22
        for i, s in enumerate(("P0", "P1", "P2")):
            vals = [100 * (look.get((m, s), {}).get(key) or 0) for m in models]
            ax.bar(x + (i - 1) * (w + 0.03), vals, width=w, color=COL[s], label=f"{s} {STRATEGY_NAMES[s]}",
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
    fig.legend(handles, labels, loc="upper center", ncol=4, fontsize=6.8, bbox_to_anchor=(0.5, 1.02),
               handlelength=1.4, columnspacing=1.4)
    fig.subplots_adjust(top=0.84, bottom=0.12, left=0.07, right=0.99)
    for fmt in ("pdf", "png"):
        fig.savefig(FIG / f"fig_coverage_mutation.{fmt}", dpi=300)
    plt.close(fig)


def fig_heatmap(rows, models):
    cols = [(m, s) for m in models for s in ("P0", "P1", "P2")]
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
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=5.6,
                    color="white" if v >= 62 else INK)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([s for _, s in cols], fontsize=6.2)
    ax.set_yticks(range(len(SPECS)))
    ax.set_yticklabels([f"{s.id} {s.name}" for s in SPECS], fontsize=6.2, color=INK)
    for k, m in enumerate(models):
        ax.text(3 * k + 1, -1.15, MODEL_NAMES.get(m, m), ha="center", va="bottom", fontsize=6.4, color=INK)
        if k:
            ax.axvline(3 * k - 0.5, color="white", lw=2.0)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=6, length=0)
    cb.set_label("rule coverage (%)", fontsize=6.4, color=INK2)
    fig.subplots_adjust(left=0.42, right=0.94, top=0.90, bottom=0.08)
    for fmt in ("pdf", "png"):
        fig.savefig(FIG / f"fig_heatmap_rule_coverage.{fmt}", dpi=300)
    plt.close(fig)


def fig_validation(agg, models):
    look = {(a["model"], a["strategy"]): a for a in agg}
    panels = [("tables_clean", "Tables with no\nstructural issue (of 12)", 1, 12),
              ("table_accuracy", "Table accuracy on\nevaluation probes (%)", 100, 100),
              ("gt_rules_with_gap", "Ground-truth rules with a\nmissing combination", 1, None)]
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 1.95), gridspec_kw={"wspace": 0.38})
    for ax, (key, label, scale, ymax) in zip(axes, panels):
        x = np.arange(len(models))
        w = 0.3
        for i, s in enumerate(("P1", "P2")):
            vals = [scale * (look.get((m, s), {}).get(key) or 0) for m in models]
            ax.bar(x + (i - 0.5) * (w + 0.04), vals, width=w, color=COL[s], zorder=3,
                   label=f"{s} {STRATEGY_NAMES[s]}")
        ax.set_xticks(x)
        ax.set_xticklabels([MODEL_NAMES.get(m, m) for m in models], fontsize=6.6, color=INK)
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
    fig.subplots_adjust(top=0.72, bottom=0.12, left=0.05, right=0.99)
    for fmt in ("pdf", "png"):
        fig.savefig(FIG / f"fig_validation_repair.{fmt}", dpi=300)
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
        for i, s in enumerate(("P0", "P1", "P2")):
            a = look.get((m, s))
            if not a:
                continue
            name = MODEL_NAMES.get(m, m) if i == 0 else ""
            lines.append(f"{name} & {s} {STRATEGY_NAMES[s]} & {a['tests_total']} & {pct(a['validity'])} & "
                         f"{pct(a['oracle_accuracy'])} & {pct(a['rule_coverage_pooled'])} & "
                         f"{a['missed_total']} & {pct(a['mutation_score_pooled'])} \\\\")
        lines.append(r"\addlinespace")
    ref = look.get(("ground-truth", "REF"))
    if ref:
        lines.append(f"GT reference & one test per GT rule & {ref['tests_total']} & {pct(ref['validity'])} & "
                     f"{pct(ref['oracle_accuracy'])} & {pct(ref['rule_coverage_pooled'])} & {ref['missed_total']} & "
                     f"{pct(ref['mutation_score_pooled'])} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    (TAB / "tab_main_results.tex").write_text("\n".join(lines) + "\n")


def tab_tables(agg, models):
    look = {(a["model"], a["strategy"]): a for a in agg}
    lines = [r"\begin{table}[t]", r"\centering",
             r"\caption{Decision-table quality before (P1) and after (P2) repair.}", r"\label{tab:tables}", r"\footnotesize", r"\setlength{\tabcolsep}{2.6pt}",
             r"\begin{tabular}{@{}llrrrrrr@{}}", r"\toprule",
             r"Model & & Usable & Clean & Acc. (\%) & Gap (\%) & Confl. (\%) & Correct (\%) \\", r"\midrule"]
    for m in models:
        for i, s in enumerate(("P1", "P2")):
            a = look.get((m, s))
            if not a:
                continue
            name = MODEL_NAMES.get(m, m) if i == 0 else ""
            lines.append(f"{name} & {s} & {a['tables_usable']}/12 & {a['tables_clean']}/12 & "
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
        for s1, s2 in (("P0", "P1"), ("P1", "P2"), ("P0", "P2")):
            stats.append(paired(rows, metric, s1, s2))
    stats.append(paired(rows, "probe_accuracy", "P1", "P2"))
    stats.append(paired(rows, "rule_correctness", "P1", "P2"))
    (RES / "stats.json").write_text(json.dumps(stats, indent=1))
    tab_benchmark(bench)
    if models:
        tab_main(agg, models)
        tab_tables(agg, models)
        fig_coverage(agg, models)
        fig_heatmap(rows, models)
        fig_validation(agg, models)
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
