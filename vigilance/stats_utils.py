from collections import defaultdict

def compute_vigilance_stats(outputs):
    stats = defaultdict(lambda: {"total": 0, "high": 0, "low": 0, "withheld": 0})

    for r in outputs:
        style = r["style_type"]
        v = r["teacher_epistemic_vigilance"]

        stats[style]["total"] += 1
        stats[style][v] += 1

    print("\n=== Epistemic Vigilance Stats ===")
    for style, s in stats.items():
        total = s["total"]
        high = s["high"]
        low = s["low"]
        withheld = s["withheld"]

        failure_rate = low / total if total > 0 else 0.0
        high_rate = high / total if total > 0 else 0.0
        withheld_rate = withheld / total if total > 0 else 0.0

        print(
            f"{style:12s} | "
            f"fail={failure_rate:.3f} | "
            f"high={high_rate:.3f} | "
            f"withheld={withheld_rate:.3f} | "
            f"(counts: H={high}, L={low}, W={withheld}, N={total})"
        )

    print("=================================\n")

    return stats