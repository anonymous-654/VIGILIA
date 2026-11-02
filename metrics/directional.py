"""Across-model paired directional contrasts from saved pairwise counts."""

import csv
import re
from collections import defaultdict
from pathlib import Path

from scipy.stats import binomtest

from metrics.heatmap import DEFAULT_EXCLUDE_PHENOMENA, model_label, normalize

CONSTRUCTS = {
    "main": "Rhetorical framing",
    "language_phen": "Linguistic phenomena",
    "dialect_phen": "Dialect phenomenon",
    "dialect_speaker": "Dialectal realization",
}


def display(label):
    return {
        "plain": "Baseline",
        "baseline": "Baseline",
        "hedge_verb_phrases": "Hedging",
        "certainty": "Certainty",
        "aave": "AAVE",
    }.get(label, label.replace("_", " ").capitalize())


def tex(text):
    return text.replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")


def generate_directional(results_root, exclude_models=None, exclude_phenomena=None):
    results_root = Path(results_root)
    excluded_models = {normalize(x) for x in (exclude_models or [])}
    excluded = {
        normalize(x)
        for x in (
            DEFAULT_EXCLUDE_PHENOMENA
            if exclude_phenomena is None
            else exclude_phenomena
        )
    }
    models = []
    counts = defaultdict(lambda: [0, 0, 0, 0])
    for path in sorted(results_root.glob("*/pairwise.csv")):
        model = path.parent.name
        if (
            normalize(model) in excluded_models
            or normalize(model_label(model)) in excluded_models
        ):
            continue
        models.append(model)
        for row in csv.DictReader(path.open()):
            family = row["family"]
            if family not in CONSTRUCTS:
                continue
            if family == "language_phen" and not re.search(
                r"_degree1_language_phen_vigilance_eval$", row["evaluation"]
            ):
                continue
            a, b = row["label_a"], row["label_b"]
            if any(normalize(x) in excluded for x in (a, b)):
                continue
            baseline = "plain" if family == "main" else "baseline"
            if baseline in (a, b):
                desired = (baseline, b if a == baseline else a)
            elif family == "main" and {a, b} == {"credibility", "anecdote"}:
                desired = ("credibility", "anecdote")
            elif family == "language_phen" and {a, b} == {
                "certainty",
                "hedge_verb_phrases",
            }:
                desired = ("certainty", "hedge_verb_phrases")
            else:
                continue
            forward = (a, b) == desired
            failures_a, failures_b = int(row["n_failures_a"]), int(row["n_failures_b"])
            inc, dec = int(row["n_a_nonfailure_b_failure"]), int(
                row["n_a_failure_b_nonfailure"]
            )
            bucket = counts[(family, *desired, model)]
            for index, value in enumerate(
                (
                    int(row["n_pairs"]),
                    (failures_b - failures_a) if forward else (failures_a - failures_b),
                    inc if forward else dec,
                    dec if forward else inc,
                )
            ):
                bucket[index] += value
    if not models:
        return None
    keys = sorted(
        {k[:3] for k in counts},
        key=lambda k: (
            list(CONSTRUCTS).index(k[0]),
            k[1] not in ("baseline", "plain"),
            k[1],
            k[2],
        ),
    )
    target = results_root / "comparison"
    target.mkdir(parents=True, exist_ok=True)
    flat, markdown_rows, latex_rows = [], [], []
    for family, a, b in keys:
        construct = (
            "Epistemic stance"
            if family == "language_phen"
            and {a, b} <= {"baseline", "certainty", "hedge_verb_phrases"}
            else CONSTRUCTS[family]
        )
        cells = []
        for model in models:
            n, difference, inc, dec = counts.get((family, a, b, model), (0, 0, 0, 0))
            delta = 100 * difference / n if n else None
            p = (
                binomtest(inc, inc + dec, 0.5).pvalue
                if n and inc + dec
                else (1.0 if n else None)
            )
            flat.append(
                dict(
                    construct=construct,
                    family=family,
                    label_a=a,
                    label_b=b,
                    model=model,
                    n_pairs=n,
                    delta_vfr_pp=delta,
                    mcnemar_p_raw=p,
                    n_increases=inc,
                    n_decreases=dec,
                )
            )
            cells.append("—" if n == 0 else f"{delta:+.2f} (p={p:.3g})")
        markdown_rows.append(
            "| "
            + " | ".join([construct, f"{display(a)} → {display(b)}", *cells])
            + " |"
        )
        latex_cells = [r"\textemdash" if c == "—" else c for c in cells]
        latex_rows.append(
            " & ".join(
                [
                    tex(construct),
                    tex(display(a)) + r" $\rightarrow$ " + tex(display(b)),
                    *latex_cells,
                ]
            )
            + r" \\"
        )
    with (target / "directional_contrasts.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(flat[0]) if flat else ["construct", "model"]
        )
        writer.writeheader()
        writer.writerows(flat)
    note = (
        "Values are paired ΔVFR (B − A) in percentage points, followed by two-sided exact McNemar p-values (raw, unadjusted). "
        "Positive values indicate more failures under B. Both realizations must validate as INCORRECT and be evaluated. "
        "Only degree-1 linguistic phenomena are included; comparison-run exclusions apply. "
        "Multiple runs of the same contrast are pooled by matched-pair counts. Missing pairs are shown as —. "
        "Each contrast can have a different matched sample; direct contrasts are computed from their own pairs, not differences between baseline contrasts."
    )
    header = ["Construct", "Contrast", *map(model_label, models)]
    (target / "directional_contrasts.md").write_text(
        "\n".join(
            [
                "# Directional linguistic contrasts",
                "",
                note,
                "",
                "| " + " | ".join(header) + " |",
                "| " + " | ".join(["---"] * len(header)) + " |",
                *markdown_rows,
                "",
                "[LaTeX table](directional_contrasts.tex) · [Counts and p-values CSV](directional_contrasts.csv)",
                "",
            ]
        )
    )
    latex = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\scriptsize",
        r"\begin{tabular}{ll" + "c" * len(models) + "}",
        r"\toprule",
        " & ".join(r"\textbf{" + tex(h) + "}" for h in header) + r" \\",
        r"\midrule",
        *latex_rows,
        r"\bottomrule",
        r"\end{tabular}",
        r"\caption{\textbf{Directional differences across linguistic contrasts.} Values report paired changes in Vigilance Failure Rate ($\Delta$VFR) in percentage points and raw two-sided exact McNemar p-values. Positive values indicate more failures under the second realization.}",
        r"\label{tab:directional_contrasts}",
        r"\end{table*}",
        "",
    ]
    (target / "directional_contrasts.tex").write_text("\n".join(latex))
    return target
