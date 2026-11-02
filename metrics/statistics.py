"""Exact McNemar test and reproducible paired bootstrap delta intervals."""

import random
import zlib


def paired_statistics(pairs, n_bootstrap=5000, seed=42, identity=""):
    if not pairs:
        return dict(
            difference_ci_low=None,
            difference_ci_high=None,
            mcnemar_statistic=None,
            p_value=None,
        )
    increases = sum(a == 0 and b == 1 for a, b in pairs)
    decreases = sum(a == 1 and b == 0 for a, b in pairs)
    discordant = increases + decreases
    statistic = min(increases, decreases)
    coefficient = cumulative = 1
    for i in range(1, statistic + 1):
        coefficient = coefficient * (discordant - i + 1) // i
        cumulative += coefficient
    p = min(1.0, 2 * (cumulative / (2**discordant))) if discordant else 1.0
    low = high = None
    if n_bootstrap:
        rng = random.Random(seed + zlib.crc32(identity.encode()))
        diffs = [b - a for a, b in pairs]
        samples = sorted(
            sum(rng.choice(diffs) for _ in diffs) / len(diffs)
            for _ in range(n_bootstrap)
        )

        def percentile(q):
            pos = (len(samples) - 1) * q
            index = int(pos)
            return samples[index] + (
                samples[min(index + 1, len(samples) - 1)] - samples[index]
            ) * (pos - index)

        low, high = percentile(0.025), percentile(0.975)
    return dict(
        difference_ci_low=low,
        difference_ci_high=high,
        mcnemar_statistic=statistic,
        p_value=p,
    )
