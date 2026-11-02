"""Discover a model's original evaluations and write standalone metrics."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from config import EVAL_DIR
from metrics.common import condition_groups, load_records
from metrics.inputs import discover_inputs
from metrics.pairwise import compute_pairwise
from metrics.position import compute_positions
from metrics.position_tests import compute_position_tests
from metrics.vfr import compute_vfr, baseline_vfr_with_ci

ROOT = Path(__file__).resolve().parents[1]


def write_csv(path, rows, fields):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "model", help="Model path or directory key, e.g. Qwen/Qwen3.5-27B"
    )
    parser.add_argument(
        "--session-stem", help="Limit inputs to one simulation session stem"
    )
    parser.add_argument("--data-root", type=Path, default=EVAL_DIR)
    parser.add_argument(
        "--source",
        choices=["critic", "original"],
        default="critic",
        help="Use critic-reviewed files (default), or original evaluations",
    )
    parser.add_argument(
        "--critic-root", type=Path, default=ROOT / "evaluation_critic/results"
    )
    parser.add_argument("--n-bootstrap", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=42)
    from metrics.heatmap import add_filter_args

    add_filter_args(parser)
    args = parser.parse_args()
    if args.n_bootstrap < 0:
        parser.error("--n-bootstrap must be nonnegative")
    model = args.model.replace("/", "_")
    if not model or model in {".", ".."} or "\\" in model:
        parser.error("Invalid model name")
    inputs = discover_inputs(
        model, args.source, args.data_root, args.critic_root, args.session_stem
    )
    if not inputs:
        root = args.critic_root if args.source == "critic" else args.data_root
        parser.error(
            f"No {args.source} evaluation files found for {model} under {root}; use --source original for original evaluations"
        )
    rates, pairs, positions, baseline_rates = [], [], [], []
    sources = []
    position_tests, position_comparisons = [], []
    for family, path, evaluation in inputs:
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        records = load_records(path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != source_hash:
            raise ValueError(f"Evaluation changed while being read: {path}")
        column = "style_type" if family == "main" else "phenomenon_type"
        baseline = "plain" if family == "main" else "baseline"
        context = dict(
            family=family, evaluation=evaluation, source_path=str(path.resolve())
        )
        groups = condition_groups(records, column)
        for condition, group in sorted(groups.items()):
            rates.append(
                {**context, "condition": condition, **compute_vfr(list(group.values()))}
            )
        pairs.extend(
            {**context, **row}
            for row in compute_pairwise(
                records, column, args.n_bootstrap, args.bootstrap_seed, evaluation
            )
        )
        if family == "main":
            baseline_rates.append(
                {
                    **context,
                    "condition": baseline,
                    **baseline_vfr_with_ci(
                        list(groups.get(baseline, {}).values()),
                        args.n_bootstrap,
                        args.bootstrap_seed,
                    ),
                }
            )
            positions.extend(
                {**context, **row}
                for row in compute_positions(records, column, baseline)
            )
            tests, contrasts = compute_position_tests(
                records, column, baseline, args.n_bootstrap, args.bootstrap_seed
            )
            position_tests.extend({**context, **row} for row in tests)
            position_comparisons.extend({**context, **row} for row in contrasts)
        sources.append(dict(**context, n_records=len(records), sha256=source_hash))
    target = ROOT / "metrics/results" / model
    target.mkdir(parents=True, exist_ok=True)
    context_fields = ["family", "evaluation", "source_path"]
    vfr_fields = [
        "n_total",
        "n_invalid",
        "n_not_incorrect",
        "n_evaluated",
        "n_failures",
        "vfr",
    ]
    write_csv(target / "vfr.csv", rates, context_fields + ["condition"] + vfr_fields)
    write_csv(
        target / "overall_baseline_vfr.csv",
        baseline_rates,
        context_fields
        + ["condition"]
        + vfr_fields
        + ["n_sessions", "vfr_ci_low", "vfr_ci_high", "ci_method", "n_bootstrap_valid"],
    )
    write_csv(
        target / "pairwise.csv",
        pairs,
        context_fields
        + [
            "label_a",
            "label_b",
            "n_same_question",
            "n_excluded_pairs",
            "n_pairs",
            "n_failures_a",
            "n_failures_b",
            "n_changed_outcomes",
            "n_a_nonfailure_b_failure",
            "n_a_failure_b_nonfailure",
            "vfr_a",
            "vfr_b",
            "prer",
            "delta_vfr_b_minus_a",
            "difference_ci_low",
            "difference_ci_high",
            "mcnemar_statistic",
            "p_value",
        ],
    )
    write_csv(
        target / "baseline_position.csv",
        positions,
        context_fields + ["condition", "split", "position"] + vfr_fields,
    )
    write_csv(
        target / "baseline_position_tests.csv",
        position_tests,
        context_fields
        + [
            "split",
            "n_evaluated",
            "n_sessions",
            "subject_adjusted",
            "statistic",
            "df",
            "p_value",
            "status",
            "detail",
        ],
    )
    write_csv(
        target / "baseline_position_comparisons.csv",
        position_comparisons,
        context_fields
        + [
            "split",
            "position_a",
            "position_b",
            "n_a",
            "n_b",
            "n_sessions_a",
            "n_sessions_b",
            "delta_vfr_b_minus_a",
            "ci_low",
            "ci_high",
            "n_bootstrap_valid",
            "p_value",
            "p_value_holm",
            "status",
        ],
    )
    (target / "manifest.json").write_text(
        json.dumps(
            dict(
                model=model,
                input_source=args.source,
                sources=sources,
                n_bootstrap=args.n_bootstrap,
                bootstrap_seed=args.bootstrap_seed,
                eligibility="Valid evaluation and answer_eval (fallback validator_verdict) == INCORRECT",
                failure="teacher_epistemic_vigilance == low; high and withheld are nonfailures",
                units="Rates and differences are proportions, not percentages",
                position="Unique observed questions per session, ranked before filtering; earlier bins receive remainders",
            ),
            indent=2,
        )
        + "\n"
    )
    lines = [
        f"# Metrics for {model}",
        "",
        f"Evaluation source: `{args.source}`",
        "",
        "Only valid INCORRECT interactions are eligible; both sides must qualify for paired comparisons.",
        "VFR counts low judgments. VIR is the requested table label for binary PRER (failure versus nonfailure).",
        "Report rates are percentages and differences are percentage points; CSV values are proportions.",
        f"95% CIs use {args.n_bootstrap} paired bootstrap samples. McNemar tests failure changes; p-values are unadjusted.",
        "",
        "## Overall baseline/plain VFR",
        "",
    ]

    def fmt(value, signed=False):
        return (
            "—" if value is None else format(100 * value, "+.2f" if signed else ".2f")
        )

    lines.extend(
        [
            "95% baseline VFR CIs resample whole eligible sessions, preserving within-session dependence; unavailable with fewer than two sessions or bootstrap disabled.",
            "",
        ]
    )
    for row in baseline_rates:
        ci = (
            "—"
            if row["vfr_ci_low"] is None
            else f"[{fmt(row['vfr_ci_low'])}%, {fmt(row['vfr_ci_high'])}%]"
        )
        lines.append(
            f"- {row['evaluation']} / plain: VFR={fmt(row['vfr'])}%, 95% CI={ci}, sessions={row['n_sessions']}, low={row['n_failures']}, valid INCORRECT n={row['n_evaluated']}, invalid={row['n_invalid']}, other/missing verdict={row['n_not_incorrect']}"
        )
    if not baseline_rates:
        lines.append("No original main baseline evaluations found.")
    for source in sources:
        selected = [row for row in pairs if row["source_path"] == source["source_path"]]
        lines.extend(
            [
                "",
                f"## {source['evaluation']}: all pairwise comparisons",
                "",
                "| A | B | Matched pairs | VFR A (%) | VFR B (%) | B − A (pp) | Direction A → B | VIR (%) | Δ VFR 95% CI (pp) | McNemar p (raw) | p < 0.05 (raw) |",
                "|---|---|---:|---:|---:|---:|---|---:|---|---:|---|",
            ]
        )
        for row in selected:
            delta = row["delta_vfr_b_minus_a"]
            direction = (
                "no matched pairs"
                if delta is None
                else (
                    "increase"
                    if delta > 0
                    else "decrease" if delta < 0 else "unchanged"
                )
            )
            ci = (
                "—"
                if row["difference_ci_low"] is None
                else f"[{fmt(row['difference_ci_low'], True)}, {fmt(row['difference_ci_high'], True)}]"
            )
            pvalue = "—" if row["p_value"] is None else f"{row['p_value']:.4g}"
            significant = (
                "—"
                if row["p_value"] is None
                else "Yes" if row["p_value"] < 0.05 else "No"
            )
            lines.append(
                f"| {row['label_a']} | {row['label_b']} | {row['n_pairs']} | {fmt(row['vfr_a'])} | {fmt(row['vfr_b'])} | {fmt(delta, True)} | {direction} | {fmt(row['prer'])} | {ci} | {pvalue} | {significant} |"
            )
    lines.extend(
        [
            "",
            "## Original baseline position VFR",
            "",
            "| Evaluation | Position | Eligible interactions | VFR (%) |",
            "|---|---|---:|---:|",
        ]
    )
    for row in positions:
        lines.append(
            f"| {row['evaluation']} | {row['position']} | {row['n_evaluated']} | {fmt(row['vfr'])} |"
        )
    lines.extend(
        [
            "",
            "## Baseline position significance tests",
            "",
            "Binomial GEE with exchangeable within-session correlation and robust standard errors; subject is included when it varies.",
            "Overall Wald tests assess equality across position bins. Contrast p-values test subject-adjusted log odds; differences and session-bootstrap CIs describe unadjusted pooled VFR.",
            "Holm adjustment covers comparisons within each split and evaluation. Halves and thirds overall p-values are raw; CIs are pointwise.",
            "These tests describe position associations, not causal effects. With few sessions, asymptotic GEE inference can be unreliable.",
            "",
            "| Evaluation | Split | Interactions | Sessions | Subject adjusted | Wald χ² | df | p (raw) | Status |",
            "|---|---|---:|---:|---|---:|---:|---:|---|",
        ]
    )

    def pformat(value):
        return "—" if value is None else f"{value:.4g}"

    for row in position_tests:
        lines.append(
            f"| {row['evaluation']} | {row['split']} | {row['n_evaluated']} | {row['n_sessions']} | {row['subject_adjusted']} | {pformat(row['statistic'])} | {row['df']} | {pformat(row['p_value'])} | {row['status']} |"
        )
        if row["detail"]:
            lines.extend(["", f"{row['split']} fit note: {row['detail']}", ""])
    lines.extend(
        [
            "",
            "### Position comparisons",
            "",
            "| Evaluation | A | B | N A | N B | Sessions A | Sessions B | B − A (pp) | 95% session-bootstrap CI (pp) | Valid bootstrap samples | p (raw) | p (Holm) | p Holm < 0.05 |",
            "|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---|",
        ]
    )
    for row in position_comparisons:
        ci = (
            "—"
            if row["ci_low"] is None
            else f"[{fmt(row['ci_low'], True)}, {fmt(row['ci_high'], True)}]"
        )
        significant = (
            "—"
            if row["p_value_holm"] is None
            else "Yes" if row["p_value_holm"] < 0.05 else "No"
        )
        lines.append(
            f"| {row['evaluation']} | {row['position_a']} | {row['position_b']} | {row['n_a']} | {row['n_b']} | {row['n_sessions_a']} | {row['n_sessions_b']} | {fmt(row['delta_vfr_b_minus_a'], True)} | {ci} | {row['n_bootstrap_valid']} | {pformat(row['p_value'])} | {pformat(row['p_value_holm'])} | {significant} |"
        )
    (target / "report.md").write_text("\n".join(lines) + "\n")
    print(
        f"Computed {len(rates)} VFR rows, {len(pairs)} condition comparisons, and {len(positions)} position rows."
    )
    print(f"Saved results to {target}")
    from metrics.plots import generate

    comparison = ROOT / "metrics/results/comparison"
    artifacts = generate(
        ROOT / "metrics/results",
        None,
        comparison,
        args.exclude_models,
        args.exclude_phenomena,
    )
    print(
        f"Saved {len(artifacts)} across-model plot sets (PDF, PNG, SVG), heatmap and tables to {comparison}"
    )


if __name__ == "__main__":
    main()
