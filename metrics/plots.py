"""Generate across-model publication plots from saved metrics, without evaluation calls."""

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

from metrics.heatmap import (
    ROOT,
    add_filter_args,
    model_label,
    normalize,
    generate_heatmap,
)

COLORS = ["#8FB9D9", "#E5A98D", "#91C9B4", "#C9A6C9", "#E8C887"]
VFR_LABEL_COLORS = ["#426F91", "#995C42", "#467C68", "#805D80", "#8C6F30"]
CATEGORY_COLORS = ["#A9C9E2", "#A8D5BA", "#D2B6D8", "#F1C6A8", "#E6D59A"]
POSITION_COLORS = COLORS + ["#B7B8D9", "#D8A8B5", "#86BFC0", "#B4C587", "#B7B0A6"]
CATEGORIES = [
    "error_adoption_propagation",
    "selective_verification",
    "conclusion_anchoring",
    "inaccurate_correction",
    "other",
]
CATEGORY_LABELS = [
    "Error adoption & propagation",
    "Selective verification",
    "Conclusion anchoring",
    "Inaccurate correction",
    "Other",
]


def read_rows(path):
    if not path.exists():
        return []
    with path.open() as handle:
        return list(csv.DictReader(handle))


def display_name(model):
    label = model_label(model)
    for old, new in [
        ("gemini-", "Gemini "),
        ("claude-haiku-4-5", "Claude Haiku 4.5"),
        ("gemma-4-", "Gemma 4 "),
        ("Qwen3.", "Qwen 3."),
    ]:
        label = label.replace(old, new)
    return label.replace("-flash", " Flash").replace("-it", "")


def generate(
    results_root,
    failure_counts,
    output_dir,
    exclude_models=None,
    exclude_phenomena=None,
    failure_results_root=ROOT / "failure_mode/results",
):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    excluded = {normalize(m) for m in (exclude_models or [])}

    def included(model):
        return not {normalize(model), normalize(model_label(model))} & excluded

    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = []
    notes = []
    if failure_counts is None:
        if any(failure_results_root.glob("*/*/classifications.json")):
            from failure_mode.aggregate import aggregate

            aggregation_dir = failure_results_root.parent / "aggregation"
            aggregate(failure_results_root, aggregation_dir)
            failure_counts = aggregation_dir / "category_counts.csv"
            print(
                f"Refreshed failure category counts from {failure_results_root}",
                flush=True,
            )
        else:
            notes.append(
                f"No saved failure classifications found in {failure_results_root}."
            )
    failure_rows = read_rows(failure_counts) if failure_counts is not None else []

    def save(fig, name):
        fig.tight_layout(pad=0.6)
        for ext in ("pdf", "png", "svg"):
            fig.savefig(output_dir / f"{name}.{ext}", bbox_inches="tight", dpi=200)
        plt.close(fig)
        artifacts.append(name)

    def clean(ax):
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_linewidth(0.6)
        ax.tick_params(axis="y", length=0, pad=4)
        ax.tick_params(axis="x", length=3, width=0.6)

    with plt.rc_context({"font.family": "STIXGeneral", "font.size": 8}):
        baseline = []
        for path in sorted(results_root.glob("*/overall_baseline_vfr.csv")):
            if included(path.parent.name):
                baseline.extend(
                    dict(row, model=path.parent.name)
                    for row in read_rows(path)
                    if row["vfr"]
                )
        baseline.sort(key=lambda r: float(r["vfr"]), reverse=True)
        duplicates = Counter(r["model"] for r in baseline)
        if baseline:
            fig, ax = plt.subplots(figsize=(6.8, max(2.7, 0.36 * len(baseline) + 0.7)))
            labels = []
            for i, row in enumerate(baseline):
                color = COLORS[i % len(COLORS)]
                value = 100 * float(row["vfr"])
                low, high = row["vfr_ci_low"], row["vfr_ci_high"]
                end = value
                if low and high:
                    low, high = 100 * float(low), 100 * float(high)
                    ax.hlines(i, low, high, color=color, linewidth=2.2)
                    ax.vlines(
                        [low, high], i - 0.08, i + 0.08, color=color, linewidth=1.5
                    )
                    end = high
                ax.scatter(
                    value,
                    i,
                    s=42,
                    color=color,
                    edgecolor="white",
                    linewidth=0.7,
                    zorder=3,
                )
                ax.annotate(
                    f"{value:.1f} ({row['n_evaluated']})"
                    + ("" if row["vfr_ci_low"] else " [CI unavailable]"),
                    (end, i),
                    xytext=(5, 0),
                    textcoords="offset points",
                    va="center",
                    fontsize=7.5,
                )
                labels.append(
                    display_name(row["model"])
                    + (
                        f" / run {sum(r['model'] == row['model'] for r in baseline[:i+1])}"
                        if duplicates[row["model"]] > 1
                        else ""
                    )
                )
            ax.set_yticks(range(len(labels)), labels)
            for i, tick in enumerate(ax.get_yticklabels()):
                tick.set_color(VFR_LABEL_COLORS[i % len(VFR_LABEL_COLORS)])
                tick.set_fontweight("semibold")
            ax.invert_yaxis()
            ax.set(xlim=(0, 100), xlabel="VFR (%)")
            ax.grid(axis="x", linestyle="--", linewidth=0.5, alpha=0.18)
            ax.set_axisbelow(True)
            clean(ax)
            save(fig, "vfr_point_range")
            with (output_dir / "vfr_point_range.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(baseline[0]))
                writer.writeheader()
                writer.writerows(baseline)
        else:
            notes.append("No saved baseline VFR rows available.")
        counts = defaultdict(Counter)
        for row in failure_rows:
            if included(row["model"]):
                if row["category"] not in CATEGORIES:
                    raise ValueError(f"Unknown failure category: {row['category']}")
                counts[row["model"]][row["category"]] += int(row["count"])
        metric_models = {
            p.parent.name
            for p in results_root.glob("*/vfr.csv")
            if included(p.parent.name)
        }
        metric_models.update(r["model"] for r in baseline)
        models = sorted(metric_models | set(counts))
        if models:
            data = np.array(
                [
                    [
                        (
                            100 * counts[m][c] / sum(counts[m].values())
                            if sum(counts[m].values())
                            else 0
                        )
                        for c in CATEGORIES
                    ]
                    for m in models
                ]
            )
            fig, ax = plt.subplots(figsize=(6.8, max(2.8, 0.36 * len(models) + 1)))
            left = np.zeros(len(models))
            for i, (label, color) in enumerate(zip(CATEGORY_LABELS, CATEGORY_COLORS)):
                ax.barh(
                    range(len(models)),
                    data[:, i],
                    left=left,
                    height=0.55,
                    color=color,
                    edgecolor="white",
                    linewidth=0.7,
                    label=label,
                )
                for j, value in enumerate(data[:, i]):
                    if value >= 8:
                        ax.text(
                            left[j] + value / 2,
                            j,
                            f"{value:.1f}",
                            ha="center",
                            va="center",
                            fontsize=7,
                        )
                left += data[:, i]
            coverage = []
            for j, model in enumerate(models):
                n = sum(counts[model].values())
                coverage.append(
                    dict(
                        model=model,
                        n_classified=n,
                        status="available" if n else "no_classified_failures",
                    )
                )
                if not n:
                    ax.text(
                        2,
                        j,
                        "No classified failures",
                        va="center",
                        color="#666",
                        fontsize=7.5,
                    )
                    notes.append(
                        f"{display_name(model)}: no classified failures available; no distribution shown."
                    )
            with (output_dir / "failure_plot_coverage.csv").open(
                "w", newline=""
            ) as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=["model", "n_classified", "status"]
                )
                writer.writeheader()
                writer.writerows(coverage)
            ax.set_yticks(range(len(models)), [display_name(m) for m in models])
            ax.invert_yaxis()
            ax.set(xlim=(0, 100), xlabel="Distribution of failure types (%)")
            ax.set_xticks(range(0, 101, 20), [f"{x}%" for x in range(0, 101, 20)])
            ax.legend(
                loc="lower center",
                bbox_to_anchor=(0.5, 1.02),
                ncol=3,
                frameon=False,
                fontsize=7,
            )
            clean(ax)
            save(fig, "failure_categories_stacked_bar")
        else:
            notes.append(f"No classified failure counts available in {failure_counts}.")
        positions = defaultdict(list)
        position_paths = sorted(results_root.glob("*/baseline_position.csv"))

        def position_family(model):
            return normalize(model_label(model).removesuffix("-nt"))

        # Assign colors before exclusions, shared across halves/thirds and base/nt variants.
        families = sorted(
            {position_family(path.parent.name) for path in position_paths}
        )
        palette = (
            POSITION_COLORS
            if len(families) <= len(POSITION_COLORS)
            else [
                plt.get_cmap("turbo")(i / max(1, len(families) - 1))
                for i in range(len(families))
            ]
        )
        family_colors = dict(zip(families, palette))
        significant_positions = set()
        for path in position_paths:
            if included(path.parent.name):
                for row in read_rows(path):
                    positions[
                        (path.parent.name, row["evaluation"], row["split"])
                    ].append(row)
                for row in read_rows(path.parent / "baseline_position_tests.csv"):
                    if (
                        row["status"] == "ok"
                        and row["p_value"]
                        and float(row["p_value"]) < 0.05
                    ):
                        significant_positions.add(
                            (path.parent.name, row["evaluation"], row["split"])
                        )
        for split, bins in [
            ("halves", ["first_half", "second_half"]),
            ("thirds", ["first_third", "second_third", "third_third"]),
        ]:
            groups = [(key, rows) for key, rows in positions.items() if key[2] == split]
            if not groups:
                continue
            fig, ax = plt.subplots(figsize=(6.8, 3.4))
            for (model, evaluation, _), rows in groups:
                rates = {
                    r["position"]: 100 * float(r["vfr"]) if r["vfr"] else np.nan
                    for r in rows
                }
                label = display_name(model)
                if (model, evaluation, split) in significant_positions:
                    label += "*"
                if sum(k[0] == model for k, _ in groups) > 1:
                    label += f" / {evaluation}"
                ax.plot(
                    range(len(bins)),
                    [rates.get(b, np.nan) for b in bins],
                    marker="o",
                    color=family_colors[position_family(model)],
                    linestyle="--" if model.endswith("-nt") else "-",
                    label=label,
                )
            ax.set_xticks(
                range(len(bins)), [b.replace("_", " ").capitalize() for b in bins]
            )
            ax.set(
                ylabel="VFR (%)",
                ylim=(0, 100),
                xlabel="Within-session question position",
            )
            ax.grid(axis="y", alpha=0.18)
            ax.legend(
                frameon=False, fontsize=7, loc="upper left", bbox_to_anchor=(1, 1)
            )
            clean(ax)
            save(fig, f"baseline_position_{split}")
    comparison = generate_heatmap(results_root, exclude_models, exclude_phenomena)
    lines = [
        "# Across-model plots",
        "",
        "VFR intervals are saved 95% session-cluster bootstrap intervals. Numbers in parentheses are eligible interaction counts (sample sizes). Evaluation runs remain separate; rates are not averaged. Failure percentages use supported, completed primary classifications only.",
        "",
    ]
    lines.extend(
        [
            "Position plots share a color between each base model and its -nt variant; base lines are solid and -nt lines are dashed. Colors match across halves and thirds.",
            "",
        ]
    )
    lines.extend(
        [
            "An asterisk after a position-plot legend name indicates an overall subject-adjusted, session-clustered GEE position test with p < 0.05 for that split (halves or thirds). These p-values are unadjusted across models and splits; stars do not indicate individual pairwise comparisons.",
            "",
        ]
    )
    for name in artifacts:
        lines.extend(
            [f"![{name}]({name}.png)", "", f"[PDF]({name}.pdf) · [SVG]({name}.svg)", ""]
        )
    lines.extend(notes)
    if comparison:
        lines.extend(["", f"Heatmap and directional tables: {comparison}"])
    (output_dir / "plots.md").write_text("\n".join(lines) + "\n")
    return artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, default=ROOT / "metrics/results")
    parser.add_argument(
        "--failure-counts",
        type=Path,
        help="Use an explicit category CSV instead of refreshing saved classifications",
    )
    parser.add_argument(
        "--failure-results-root", type=Path, default=ROOT / "failure_mode/results"
    )
    parser.add_argument("--output-dir", type=Path)
    add_filter_args(parser)
    args = parser.parse_args()
    target = args.output_dir or args.results_root / "comparison"
    artifacts = generate(
        args.results_root,
        args.failure_counts,
        target,
        args.exclude_models,
        args.exclude_phenomena,
        args.failure_results_root,
    )
    print(f"Saved {len(artifacts)} plot sets (PDF, PNG, SVG) to {target}")


if __name__ == "__main__":
    main()
