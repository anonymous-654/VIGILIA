"""PRER and delta VFR use the same eligible matched questions."""

from itertools import combinations
from metrics.common import condition_groups, eligibility, failure
from metrics.statistics import paired_statistics


def compute_pairwise(records, column, n_bootstrap=5000, seed=42, identity=""):
    groups = condition_groups(records, column)
    labels = sorted(
        groups, key=lambda label: (label not in {"plain", "baseline"}, label)
    )
    results = []
    for a, b in combinations(labels, 2):
        shared = groups[a].keys() & groups[b].keys()
        pairs = [
            (failure(groups[a][k]), failure(groups[b][k]))
            for k in sorted(shared, key=lambda k: (str(k[0]), float(k[1])))
            if eligibility(groups[a][k]) == eligibility(groups[b][k]) == "eligible"
        ]
        n = len(pairs)
        failures_a = sum(x for x, _ in pairs)
        failures_b = sum(y for _, y in pairs)
        changed = sum(x != y for x, y in pairs)
        results.append(
            dict(
                label_a=a,
                label_b=b,
                n_same_question=len(shared),
                n_excluded_pairs=len(shared) - n,
                n_pairs=n,
                n_failures_a=failures_a,
                n_failures_b=failures_b,
                n_changed_outcomes=changed,
                n_a_nonfailure_b_failure=sum(x == 0 and y == 1 for x, y in pairs),
                n_a_failure_b_nonfailure=sum(x == 1 and y == 0 for x, y in pairs),
                vfr_a=failures_a / n if n else None,
                vfr_b=failures_b / n if n else None,
                prer=changed / n if n else None,
                delta_vfr_b_minus_a=(failures_b - failures_a) / n if n else None,
                **paired_statistics(pairs, n_bootstrap, seed, f"{identity}|{a}|{b}"),
            )
        )
    return results
