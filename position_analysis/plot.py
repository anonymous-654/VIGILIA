"""Aggregate saved eligible baseline observations into within-session thirds."""

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2, norm
from metrics.position_tests import holm
import warnings
from metrics.heatmap import model_label

ROOT = Path(__file__).resolve().parents[1]
LABELS = ["First third", "Second third", "Third third"]


def third(rank, total):
    size, remainder = divmod(int(total), 3)
    first = size + (remainder > 0)
    second = first + size + (remainder > 1)
    return 0 if rank <= first else (1 if rank <= second else 2)


def significance(data):
    result = dict(
        p_raw=None, p_holm=None, status="unavailable", detail="", contrasts=[]
    )
    try:
        if (
            data.session.nunique() < 2
            or data.fail.nunique() < 2
            or data.third.nunique() != 3
        ):
            raise ValueError(
                "Need multiple sessions, both outcomes, and observations in all thirds"
            )
        formula = "fail ~ C(third)" + (
            " + C(subject)" if data.subject.nunique() > 1 else ""
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fit = sm.GEE.from_formula(
                formula,
                groups="session",
                data=data,
                family=sm.families.Binomial(),
                cov_struct=sm.cov_struct.Exchangeable(),
            ).fit()
        indices = [
            i for i, name in enumerate(fit.params.index) if name.startswith("C(third)")
        ]
        beta = np.asarray(fit.params)[indices]
        cov = np.asarray(fit.cov_params())[np.ix_(indices, indices)]
        if (
            not fit.converged
            or len(indices) != 2
            or not np.all(np.isfinite(cov))
            or np.linalg.matrix_rank(cov) < 2
        ):
            raise ValueError("Invalid or nonconverged thirds GEE fit")
        result.update(
            p_raw=float(chi2.sf(beta @ np.linalg.solve(cov, beta), 2)),
            status="ok",
            detail="; ".join(str(w.message) for w in caught),
        )
        for a, b in [(0, 1), (0, 2), (1, 2)]:
            contrast = np.zeros(len(fit.params))
            for value, sign in [(a, -1), (b, 1)]:
                name = f"C(third)[T.{value}]"
                if name in fit.params.index:
                    contrast[list(fit.params.index).index(name)] += sign
            variance = float(contrast @ fit.cov_params() @ contrast)
            if variance <= 0 or not np.isfinite(variance):
                raise ValueError("Invalid contrast variance")
            estimate = float(contrast @ fit.params)
            result["contrasts"].append(
                dict(
                    position_a=LABELS[a],
                    position_b=LABELS[b],
                    p_raw=float(2 * norm.sf(abs(estimate) / np.sqrt(variance))),
                )
            )
        for row, p in zip(
            result["contrasts"], holm([c["p_raw"] for c in result["contrasts"]])
        ):
            row["p_holm"] = p
    except (ValueError, np.linalg.LinAlgError, ZeroDivisionError) as error:
        result.update(p_raw=None, status="unavailable", detail=str(error), contrasts=[])
    return result


def generate(results_root, rowsets=None):
    if rowsets is None:
        rowsets = [
            (p.parent.name, pd.read_csv(p))
            for p in sorted(results_root.glob("*/observations.csv"))
        ]
    if not rowsets:
        raise ValueError("No saved observations found; run position_analysis.run first")
    rows = []
    tests = {}
    for model, data in rowsets:
        data = data.copy()
        data["third"] = [
            third(r, n) for r, n in zip(data.question_rank, data.n_session_questions)
        ]
        tests[model] = significance(data)
        for i, label in enumerate(LABELS):
            selected = data[data.third == i]
            n = len(selected)
            failures = int(selected.fail.sum())
            rows.append(
                dict(
                    model=model,
                    third=i + 1,
                    position=label,
                    n_evaluated=n,
                    n_failures=failures,
                    n_sessions=selected.session.nunique(),
                    vfr_percent=100 * failures / n if n else None,
                )
            )
    tested = [test for test in tests.values() if test["p_raw"] is not None]
    for test, p in zip(tested, holm([t["p_raw"] for t in tested])):
        test["p_holm"] = p
    test_rows = [
        dict(
            model=model,
            p_raw=t["p_raw"],
            p_holm=t["p_holm"],
            status=t["status"],
            detail=t["detail"],
        )
        for model, t in tests.items()
    ]
    contrasts = [
        dict(model=model, **c) for model, t in tests.items() for c in t["contrasts"]
    ]
    for name, items, fields in [
        (
            "thirds_significance.csv",
            test_rows,
            ["model", "p_raw", "p_holm", "status", "detail"],
        ),
        (
            "thirds_comparisons.csv",
            contrasts,
            ["model", "position_a", "position_b", "p_raw", "p_holm"],
        ),
    ]:
        with (results_root / name).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(items)

    def pformat(value):
        return "—" if value is None else f"{value:.4g}"

    with (results_root / "thirds_vfr.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Baseline VFR by within-session third",
        "",
        "Cells show pooled VFR (%) and failures/evaluated interactions. Thirds are assigned using all observed question ranks before eligibility filtering, with extra questions assigned to earlier thirds. These are the same completed critic-reviewed baseline observations used in the continuous-position analysis; single-question sessions are excluded.",
        "",
        "| Model | First third | Second third | Third third | Overall p (raw) | Overall p (Holm) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for model, _ in rowsets:
        cells = [
            (
                f"{r['vfr_percent']:.1f} ({r['n_failures']}/{r['n_evaluated']})"
                if r["n_evaluated"]
                else "— (0/0)"
            )
            for r in rows
            if r["model"] == model
        ]
        cells += [pformat(tests[model]["p_raw"]), pformat(tests[model]["p_holm"])]
        lines.append("| " + model_label(model) + " | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Overall p-values test differences among the three thirds using a subject-adjusted binomial GEE clustered by session. Holm adjustment is across models in this table. These are categorical thirds tests, distinct from the continuous-position trend test.",
        "",
        "| Model | First vs second p (Holm) | First vs third p (Holm) | Second vs third p (Holm) |",
        "|---|---:|---:|---:|",
    ]
    for model, t in tests.items():
        cells = (
            [pformat(c["p_holm"]) for c in t["contrasts"]]
            if t["contrasts"]
            else ["—"] * 3
        )
        lines.append("| " + model_label(model) + " | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Pairwise p-values are two-sided GEE contrasts, Holm-adjusted across the three comparisons within each model. [Overall tests](thirds_significance.csv) · [Raw and adjusted pairwise tests](thirds_comparisons.csv)",
        "",
    ]
    lines += [
        "",
        "![Baseline VFR by position](thirds_vfr.png)",
        "",
        "[Paper PDF](thirds_vfr.pdf) · [SVG](thirds_vfr.svg) · [Counts and rates](thirds_vfr.csv)",
        "",
    ]
    (results_root / "thirds_vfr.md").write_text("\n".join(lines))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for model, _ in rowsets:
        values = [
            r["vfr_percent"] if r["vfr_percent"] is not None else np.nan
            for r in rows
            if r["model"] == model
        ]
        ax.plot([1, 2, 3], values, marker="o", linewidth=2, label=model_label(model))
    ax.set_xticks([1, 2, 3], LABELS)
    ax.set_xlabel("Within-session question position")
    ax.set_ylabel("VFR (%)")
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    for extension in ["png", "pdf", "svg"]:
        fig.savefig(
            results_root / f"thirds_vfr.{extension}", dpi=200, bbox_inches="tight"
        )
    plt.close(fig)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-root", type=Path, default=ROOT / "position_analysis/results"
    )
    args = parser.parse_args()
    generate(args.results_root)
    print(f"Saved thirds table and graph to {args.results_root}")
