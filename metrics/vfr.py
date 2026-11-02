"""Vigilance failure rate on valid, incorrect interactions."""

from metrics.common import eligibility, failure


def compute_vfr(records):
    selected = [row for row in records if eligibility(row) == "eligible"]
    n = len(selected)
    low = sum(failure(row) for row in selected)
    return dict(
        n_total=len(records),
        n_invalid=sum(eligibility(r) == "invalid" for r in records),
        n_not_incorrect=sum(eligibility(r) == "not_incorrect" for r in records),
        n_evaluated=n,
        n_failures=low,
        vfr=low / n if n else None,
    )


def baseline_vfr_with_ci(records, n_bootstrap=5000, seed=42):
    """Percentile bootstrap of pooled VFR, resampling eligible sessions intact."""
    import random
    from collections import defaultdict

    selected = [r for r in records if eligibility(r) == "eligible"]
    groups = defaultdict(lambda: [0, 0])
    for row in selected:
        groups[str(row["session_id"])][0] += failure(row)
        groups[str(row["session_id"])][1] += 1
    clusters = [groups[key] for key in sorted(groups)]
    result = dict(
        compute_vfr(records),
        n_sessions=len(clusters),
        vfr_ci_low=None,
        vfr_ci_high=None,
        ci_method="session_cluster_bootstrap_percentile",
        n_bootstrap_valid=0,
    )
    if len(clusters) < 2 or n_bootstrap <= 0:
        return result
    rng = random.Random(seed)
    draws = []
    for _ in range(n_bootstrap):
        sample = [rng.choice(clusters) for _ in clusters]
        draws.append(sum(x[0] for x in sample) / sum(x[1] for x in sample))
    draws.sort()

    def percentile(q):
        pos = (len(draws) - 1) * q
        index = int(pos)
        return draws[index] + (draws[min(index + 1, len(draws) - 1)] - draws[index]) * (
            pos - index
        )

    result.update(
        vfr_ci_low=percentile(0.025),
        vfr_ci_high=percentile(0.975),
        n_bootstrap_valid=len(draws),
    )
    return result
