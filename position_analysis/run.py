"""Continuous-position trends in critic-reviewed original baseline failures."""

import argparse
import csv
import hashlib
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import rankdata, norm
from metrics.common import eligibility, failure, key, load_records
from metrics.inputs import discover_inputs
from metrics.position_tests import holm
from metrics.heatmap import model_label

ROOT = Path(__file__).resolve().parents[1]


def prepare(inputs):
    rows, sources, seen = [], [], set()
    skipped_single = 0
    for _, path, stem in inputs:
        records = load_records(path)
        sessions = {}
        for r in records:
            session, question = key(r)
            sessions.setdefault(session, set()).add(question)
        ranks = {}
        for session, questions in sessions.items():
            ordered = sorted(questions, key=float)
            for i, question in enumerate(ordered):
                ranks[(session, question)] = (i, len(ordered))
        for r in records:
            if (
                r.get("style_type") != "plain"
                or eligibility(r) != "eligible"
                or r.get("evaluation_critic", {}).get("status") != "completed"
            ):
                continue
            identity = key(r)
            if identity in seen:
                raise ValueError(f"Duplicate eligible baseline interaction: {identity}")
            seen.add(identity)
            i, n = ranks[identity]
            if n < 2:
                skipped_single += 1
                continue
            rows.append(
                dict(
                    session=str(r["session_id"]),
                    question_turn_index=r["question_turn_index"],
                    question_rank=i + 1,
                    n_session_questions=n,
                    position=i / (n - 1),
                    subject=str(r.get("subject") or "unknown"),
                    fail=failure(r),
                    evaluation=stem,
                )
            )
        sources.append(
            dict(
                path=str(path.resolve()),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    return (
        pd.DataFrame(
            rows,
            columns=[
                "session",
                "question_turn_index",
                "question_rank",
                "n_session_questions",
                "position",
                "subject",
                "fail",
                "evaluation",
            ],
        ),
        sources,
        skipped_single,
    )


def rho(x, y):
    a, b = rankdata(x), rankdata(y)
    a -= a.mean()
    b -= b.mean()
    denom = np.sqrt(np.dot(a, a) * np.dot(b, b))
    return float(np.dot(a, b) / denom) if denom else None


def analyze(data, n_bootstrap, seed):
    result = dict(
        n_evaluated=len(data),
        n_sessions=data.session.nunique(),
        n_failures=int(data.fail.sum()),
        vfr=float(data.fail.mean()) if len(data) else None,
        subject_adjusted=data.subject.nunique() > 1,
        spearman_rho=None,
        rho_ci_low=None,
        rho_ci_high=None,
        n_bootstrap_valid=0,
        gee_beta=None,
        gee_beta_ci_low=None,
        gee_beta_ci_high=None,
        odds_ratio_per_10pct=None,
        odds_ratio_ci_low=None,
        odds_ratio_ci_high=None,
        gee_p_raw=None,
        gee_p_holm=None,
        gee_status="unavailable",
        gee_detail="",
    )
    if len(data):
        result["spearman_rho"] = rho(data.position.to_numpy(), data.fail.to_numpy())
    if result["spearman_rho"] is not None and data.session.nunique() > 1:
        groups = [
            group[["position", "fail"]].to_numpy(dtype=float)
            for _, group in data.groupby("session")
        ]
        rng = np.random.default_rng(seed)
        draws = []
        for _ in range(n_bootstrap):
            sample = np.concatenate(
                [groups[i] for i in rng.integers(len(groups), size=len(groups))]
            )
            value = rho(sample[:, 0], sample[:, 1])
            if value is not None:
                draws.append(value)
        result["n_bootstrap_valid"] = len(draws)
        if draws:
            result["rho_ci_low"], result["rho_ci_high"] = map(
                float, np.percentile(draws, [2.5, 97.5])
            )
    try:
        if (
            len(data) == 0
            or data.session.nunique() < 2
            or data.fail.nunique() < 2
            or data.position.nunique() < 2
        ):
            raise ValueError(
                "Need multiple sessions, both failure outcomes, and varying positions"
            )
        formula = "fail ~ position" + (
            " + C(subject)" if result["subject_adjusted"] else ""
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
        beta, se = float(fit.params["position"]), float(fit.bse["position"])
        if not fit.converged or not np.isfinite(beta) or not np.isfinite(se) or se <= 0:
            raise ValueError(
                "GEE failed to converge or returned an invalid position standard error"
            )
        low, high = beta - norm.ppf(0.975) * se, beta + norm.ppf(0.975) * se
        odds = np.exp(np.array([beta, low, high]) * 0.1)
        if not np.all(np.isfinite(odds)):
            raise ValueError("Nonfinite odds ratio or interval")
        result.update(
            gee_beta=beta,
            gee_beta_ci_low=low,
            gee_beta_ci_high=high,
            odds_ratio_per_10pct=float(odds[0]),
            odds_ratio_ci_low=float(odds[1]),
            odds_ratio_ci_high=float(odds[2]),
            gee_p_raw=float(2 * norm.sf(abs(beta / se))),
            gee_status="ok",
            gee_detail="; ".join(dict.fromkeys(str(w.message) for w in caught)),
        )
    except (ValueError, np.linalg.LinAlgError, ZeroDivisionError) as error:
        result["gee_detail"] = str(error)
    return result


def csv_save(path, rows, fields):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "models",
        nargs="*",
        help="Default: all models with original baseline critic files",
    )
    parser.add_argument(
        "--critic-root", type=Path, default=ROOT / "evaluation_critic/results"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "position_analysis/results"
    )
    parser.add_argument("--n-bootstrap", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.n_bootstrap < 0:
        parser.error("--n-bootstrap must be nonnegative")
    models = (
        [m.replace("/", "_") for m in args.models]
        if args.models
        else sorted(p.name for p in args.critic_root.iterdir() if p.is_dir())
    )
    summaries, provenance, rowsets = [], [], []
    for model in dict.fromkeys(models):
        if model in ("", ".", "..") or "/" in model or "\\" in model:
            parser.error("Invalid model name")
        inputs = [
            i
            for i in discover_inputs(
                model, "critic", ROOT / "data/evaluations", args.critic_root
            )
            if i[0] == "main"
        ]
        if not inputs:
            if args.models:
                parser.error(f"No baseline critic inputs for {model}")
            continue
        data, sources, skipped = prepare(inputs)
        result = dict(
            model=model,
            **analyze(data, args.n_bootstrap, args.seed),
            n_single_question_excluded=skipped,
        )
        summaries.append(result)
        provenance.append(dict(model=model, inputs=sources))
        rowsets.append((model, data))
        print(
            f"{model}: {result['n_evaluated']} interactions, {result['n_sessions']} sessions; GEE {result['gee_status']}",
            flush=True,
        )
    if not summaries:
        parser.error("No baseline critic evaluations found")
    tested = [r for r in summaries if r["gee_p_raw"] is not None]
    for row, p in zip(tested, holm([r["gee_p_raw"] for r in tested])):
        row["gee_p_holm"] = p
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for model, data in rowsets:
        target = args.output_dir / model
        target.mkdir(exist_ok=True)
        data.to_csv(target / "observations.csv", index=False)
    csv_save(args.output_dir / "trends.csv", summaries, list(summaries[0]))
    (args.output_dir / "summary.json").write_text(
        json.dumps(summaries, indent=2, allow_nan=False) + "\n"
    )
    (args.output_dir / "manifest.json").write_text(
        json.dumps(
            dict(n_bootstrap=args.n_bootstrap, seed=args.seed, inputs=provenance),
            indent=2,
        )
        + "\n"
    )

    def fmt(x):
        return "—" if x is None else f"{x:.3g}"

    lines = [
        "# Baseline position trends across critic-reviewed models",
        "",
        "Original main/plain baselines only. Included answers are INCORRECT, eligible, and completed by the critic. Position is (question rank − 1)/(number of observed session questions − 1), assigned before validation filtering. Low vigilance is failure; high/withheld is nonfailure. Single-question sessions are excluded.",
        "",
        "Main test: binomial logistic GEE with continuous position, subject effects when subjects vary, exchangeable within-session correlation, and robust standard errors. Odds ratios describe a 10-percentage-point advance through the session. Holm p-values adjust across the models tested in this run. Spearman correlation is supplementary and unadjusted for subject; its 95% interval resamples whole sessions. No ordinary independent-observation Spearman p-value is reported.",
        "",
        "| Model | N | Sessions | VFR (%) | Spearman ρ | ρ 95% cluster CI | OR per 10% position | OR 95% CI | GEE p (raw) | GEE p (Holm) | Trend |",
        "|---|---:|---:|---:|---:|---|---:|---|---:|---:|---|",
    ]
    for r in summaries:
        trend = "Unavailable"
        if r["gee_status"] == "ok":
            direction = "increasing" if r["gee_beta"] > 0 else "decreasing"
            trend = (
                direction.capitalize()
                if r["gee_p_holm"] < 0.05
                else f"No significant trend ({direction} estimate)"
            )
        lines.append(
            "| "
            + " | ".join(
                [
                    model_label(r["model"]),
                    str(r["n_evaluated"]),
                    str(r["n_sessions"]),
                    fmt(None if r["vfr"] is None else 100 * r["vfr"]),
                    fmt(r["spearman_rho"]),
                    f"[{fmt(r['rho_ci_low'])}, {fmt(r['rho_ci_high'])}]",
                    fmt(r["odds_ratio_per_10pct"]),
                    f"[{fmt(r['odds_ratio_ci_low'])}, {fmt(r['odds_ratio_ci_high'])}]",
                    fmt(r["gee_p_raw"]),
                    fmt(r["gee_p_holm"]),
                    trend,
                ]
            )
            + " |"
        )
    lines += [
        "",
        "These are associations with position, not causal evidence of vigilance deterioration. A linear log-odds trend can miss nonmonotonic changes; retain the existing halves/thirds analyses. Pooled Spearman estimates and subject-adjusted GEE estimates can differ. Cluster inference is approximate and is less reliable with very few sessions.",
        "",
        "[Full numerical results](trends.csv) · [Input hashes and settings](manifest.json)",
        "",
    ]
    lines.extend(
        f"- {r['model']}: {r['gee_status']}; {r['gee_detail']}"
        for r in summaries
        if r["gee_detail"]
    )
    (args.output_dir / "report.md").write_text("\n".join(lines))
    from position_analysis.plot import generate

    generate(args.output_dir, rowsets)
    with (args.output_dir / "report.md").open("a") as handle:
        handle.write(
            "\n[Aggregated VFR by thirds](thirds_vfr.md) · [Line graph PDF](thirds_vfr.pdf)\n\n![VFR by thirds](thirds_vfr.png)\n"
        )
    print(f"Saved {args.output_dir}")


if __name__ == "__main__":
    main()
