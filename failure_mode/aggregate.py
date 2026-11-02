"""Map saved primary failure classifications into five reporting categories."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = (
    "error_adoption_propagation",
    "selective_verification",
    "conclusion_anchoring",
    "inaccurate_correction",
    "other",
)


def map_category(classification):
    primary = classification.get("primary_category")
    if primary in ("error_adoption_propagation", "inaccurate_correction"):
        return primary
    if primary == "selective_verification":
        subtypes = classification.get("selective_verification_subtypes", [])
        # Existing results have one subtype. Ambiguous mixed subtypes stay other.
        if subtypes == ["conclusion_only_validation"]:
            return "conclusion_anchoring"
        if subtypes == ["correct_part_validation"]:
            return "selective_verification"
    return "other"


def write_csv(path, rows, fields):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def aggregate(results_root, output_dir):
    paths = sorted(results_root.glob("*/*/classifications.json"))
    if not paths:
        raise ValueError(f"No saved classifications found in {results_root}")
    models, records, inputs = {}, [], []
    seen = set()
    for path in paths:
        model = path.parent.parent.name
        document = json.loads(path.read_text())
        stats = models.setdefault(
            model, dict(categories=Counter(), excluded=Counter(), n_selected=0)
        )
        inputs.append(
            dict(
                path=str(path.resolve()),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
        for entry in document["records"]:
            record = entry["record"]
            identity = (model, record["session_id"], record["question_turn_index"])
            if identity in seen:
                raise ValueError(
                    f"Duplicate baseline interaction across saved inputs: {identity}"
                )
            seen.add(identity)
            review = entry["review"]
            classification = review.get("classification", {})
            assessment = classification.get(
                "assessment", review.get("status", "unknown")
            )
            supported = (
                review.get("status") == "completed"
                and assessment == "supported_failure"
                and bool(classification.get("primary_category"))
            )
            category = map_category(classification) if supported else ""
            exclusion = (
                ""
                if supported
                else (
                    review.get("status", "unknown")
                    if review.get("status") != "completed"
                    else assessment
                )
            )
            if not supported and assessment == "supported_failure":
                exclusion = "missing_primary_category"
            stats["n_selected"] += 1
            (stats["categories"] if supported else stats["excluded"])[
                category if supported else exclusion
            ] += 1
            records.append(
                dict(
                    model=model,
                    source_file=str(path.resolve()),
                    source_index=entry["source_index"],
                    session_id=record["session_id"],
                    question_turn_index=record["question_turn_index"],
                    subject=record.get("subject", ""),
                    review_status=review.get("status", ""),
                    assessment=assessment,
                    original_primary=classification.get("primary_category") or "",
                    original_subtypes="|".join(
                        classification.get("selective_verification_subtypes", [])
                    ),
                    aggregated_category=category,
                    exclusion_reason=exclusion,
                )
            )
    summary = []
    counts = []
    exclusions = []
    for model, stats in models.items():
        n = sum(stats["categories"].values())
        summary.append(
            dict(
                model=model,
                n_selected=stats["n_selected"],
                n_classified=n,
                n_excluded=sum(stats["excluded"].values()),
                category_counts={c: stats["categories"][c] for c in CATEGORIES},
                excluded_counts=dict(stats["excluded"]),
            )
        )
        for category in CATEGORIES:
            count = stats["categories"][category]
            counts.append(
                dict(
                    model=model,
                    category=category,
                    count=count,
                    percent_of_classified=100 * count / n if n else None,
                    n_classified=n,
                    n_selected=stats["n_selected"],
                )
            )
        exclusions.extend(
            dict(model=model, status=status, count=count)
            for status, count in sorted(stats["excluded"].items())
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        output_dir / "category_counts.csv",
        counts,
        [
            "model",
            "category",
            "count",
            "percent_of_classified",
            "n_classified",
            "n_selected",
        ],
    )
    write_csv(
        output_dir / "mapped_records.csv",
        records,
        list(records[0]) if records else ["model", "aggregated_category"],
    )
    write_csv(
        output_dir / "excluded_counts.csv", exclusions, ["model", "status", "count"]
    )
    (output_dir / "summary.json").write_text(
        json.dumps(
            dict(
                models=summary,
                pooled_category_counts={
                    c: sum(s["category_counts"][c] for s in summary) for c in CATEGORIES
                },
                inputs=inputs,
            ),
            indent=2,
        )
        + "\n"
    )
    lines = [
        "# Aggregated baseline failure modes",
        "",
        "Cells show count (% of supported, completed primary classifications). Secondary categories do not affect counts. Uncertain, disputed, pending, and failed reviews are excluded from the percentage denominator and reported separately.",
        "",
        "| Category | " + " | ".join(models) + " |",
        "|---|" + "---:|" * len(models),
    ]
    for category in CATEGORIES:
        cells = []
        for stats in models.values():
            n = sum(stats["categories"].values())
            count = stats["categories"][category]
            cells.append(f"{count} ({100*count/n:.1f}%)" if n else "0 (—)")
        lines.append("| " + category + " | " + " | ".join(cells) + " |")
    lines += [
        "",
        "| Model | Selected | Classified | Excluded | Exclusion details |",
        "|---|---:|---:|---:|---|",
    ]
    for s in summary:
        lines.append(
            f"| {s['model']} | {s['n_selected']} | {s['n_classified']} | {s['n_excluded']} | "
            + ", ".join(f"{k}: {v}" for k, v in s["excluded_counts"].items())
            + " |"
        )
    lines += [
        "",
        "Mapping: error adoption/propagation and inaccurate correction retain their categories. Selective verification with only `conclusion_only_validation` maps to conclusion anchoring; with only `correct_part_validation` it maps to selective verification. Remaining supported failures map to other (including incomplete correction, assessment abandonment, missing or mixed selective-verification subtypes).",
        "",
        "[Category counts](category_counts.csv) · [Record linkage](mapped_records.csv) · [Excluded counts](excluded_counts.csv) · [Summary and source hashes](summary.json)",
        "",
    ]
    (output_dir / "report.md").write_text("\n".join(lines))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-root", type=Path, default=ROOT / "failure_mode/results"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "failure_mode/aggregation"
    )
    args = parser.parse_args()
    summary = aggregate(args.results_root, args.output_dir)
    print(f"Aggregated {len(summary)} models: {args.output_dir}")


if __name__ == "__main__":
    main()
