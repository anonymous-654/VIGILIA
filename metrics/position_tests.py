"""Session-clustered inference for original baseline position associations."""

import itertools
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2, norm
from metrics.common import eligibility, failure, key
from metrics.position import position_bins


def holm(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    adjusted = [0.0] * len(values)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (len(values) - rank) * values[index]))
        adjusted[index] = running
    return adjusted


def compute_position_tests(records, column, baseline, n_bootstrap=5000, seed=42):
    bins = position_bins(records)
    eligible = [
        r for r in records if r[column] == baseline and eligibility(r) == "eligible"
    ]
    overall, comparisons = [], []
    for split, labels in [
        ("halves", ["first_half", "second_half"]),
        ("thirds", ["first_third", "second_third", "third_third"]),
    ]:
        data = pd.DataFrame(
            [
                dict(
                    session=str(r["session_id"]),
                    position=bins[key(r)][split],
                    subject=str(r.get("subject") or "unknown"),
                    fail=failure(r),
                )
                for r in eligible
            ],
            columns=["session", "position", "subject", "fail"],
        )
        sessions = sorted(data.session.unique())
        counts = np.zeros((len(sessions), len(labels), 2))
        for i, session in enumerate(sessions):
            for j, label in enumerate(labels):
                group = data[(data.session == session) & (data.position == label)]
                counts[i, j] = [group.fail.sum(), len(group)]
        total = counts.sum(axis=0)
        boot = []
        rng = np.random.RandomState(seed + (split == "thirds"))
        if sessions:
            for _ in range(n_bootstrap):
                sample = counts[rng.randint(len(sessions), size=len(sessions))].sum(
                    axis=0
                )
                boot.append(
                    np.divide(
                        sample[:, 0],
                        sample[:, 1],
                        out=np.full(len(labels), np.nan),
                        where=sample[:, 1] > 0,
                    )
                )
        boot = np.asarray(boot)
        base = dict(
            split=split,
            n_evaluated=len(data),
            n_sessions=len(sessions),
            subject_adjusted=data.subject.nunique() > 1,
            statistic=None,
            df=len(labels) - 1,
            p_value=None,
            status="unavailable",
            detail="",
        )
        result = None
        try:
            if len(sessions) < 2 or data.fail.nunique() < 2 or any(total[:, 1] == 0):
                raise ValueError(
                    "Need multiple sessions, both outcomes, and observations in every position bin"
                )
            formula = "fail ~ C(position)" + (
                " + C(subject)" if base["subject_adjusted"] else ""
            )
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result = sm.GEE.from_formula(
                    formula,
                    groups="session",
                    data=data,
                    family=sm.families.Binomial(),
                    cov_struct=sm.cov_struct.Exchangeable(),
                ).fit()
            indices = [
                i
                for i, name in enumerate(result.params.index)
                if name.startswith("C(position)")
            ]
            beta = np.asarray(result.params)[indices]
            covariance = np.asarray(result.cov_params())[np.ix_(indices, indices)]
            if (
                not result.converged
                or not np.all(np.isfinite(covariance))
                or np.linalg.matrix_rank(covariance) < len(indices)
            ):
                raise ValueError(
                    "GEE did not converge or position covariance is singular/nonfinite"
                )
            stat = float(beta @ np.linalg.solve(covariance, beta))
            base.update(
                statistic=stat,
                p_value=float(chi2.sf(stat, len(indices))),
                status="ok",
                detail="; ".join(dict.fromkeys(str(w.message) for w in caught)),
            )
        except (ValueError, np.linalg.LinAlgError, ZeroDivisionError) as error:
            base["detail"] = str(error)
            result = None
        overall.append(base)
        rows = []
        for ia, ib in itertools.combinations(range(len(labels)), 2):
            na, nb = int(total[ia, 1]), int(total[ib, 1])
            delta = total[ib, 0] / nb - total[ia, 0] / na if na and nb else None
            draws = boot[:, ib] - boot[:, ia] if boot.size else np.array([])
            draws = draws[np.isfinite(draws)]
            low, high = (
                np.percentile(draws, [2.5, 97.5]) if len(draws) else (None, None)
            )
            row = dict(
                split=split,
                position_a=labels[ia],
                position_b=labels[ib],
                n_a=na,
                n_b=nb,
                n_sessions_a=int((counts[:, ia, 1] > 0).sum()),
                n_sessions_b=int((counts[:, ib, 1] > 0).sum()),
                delta_vfr_b_minus_a=delta,
                ci_low=low,
                ci_high=high,
                n_bootstrap_valid=len(draws),
                p_value=None,
                p_value_holm=None,
                status=base["status"],
            )
            if result is not None:
                contrast = np.zeros(len(result.params))
                names = list(result.params.index)
                for label, sign in [(labels[ia], -1), (labels[ib], 1)]:
                    term = f"C(position)[T.{label}]"
                    if term in names:
                        contrast[names.index(term)] += sign
                variance = float(contrast @ result.cov_params() @ contrast)
                estimate = float(contrast @ result.params)
                if variance > 0 and np.isfinite(variance):
                    row["p_value"] = float(
                        2 * norm.sf(abs(estimate / np.sqrt(variance)))
                    )
                else:
                    row["status"] = "unavailable"
            rows.append(row)
        valid = [r for r in rows if r["p_value"] is not None]
        for row, p in zip(valid, holm([r["p_value"] for r in valid])):
            row["p_value_holm"] = p
        comparisons.extend(rows)
    return overall, comparisons
