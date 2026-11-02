"""Classify valid critic-reviewed incorrect/low plain baselines using GPT Luna."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm
from evaluation_critic.run import save
from evaluation_critic.review import model_call
from failure_mode.classify import PROMPT, classify_record
from metrics.common import eligibility
from metrics.inputs import discover_inputs

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--session-stem")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    model = args.model.replace("/", "_")
    if (
        model in {"", ".", ".."}
        or "\\" in model
        or args.workers < 1
        or (args.limit is not None and args.limit < 1)
    ):
        parser.error("Invalid model, workers or limit")
    inputs = [
        x
        for x in discover_inputs(
            model,
            "critic",
            ROOT / "data/evaluations",
            ROOT / "evaluation_critic/results",
            args.session_stem,
        )
        if x[0] == "main"
    ]
    if not inputs:
        parser.error("No main critic-reviewed evaluations found")
    any_errors = False
    for _, path, stem in inputs:
        original = json.loads(path.read_text())
        rows = [
            dict(source_index=i, record=r)
            for i, r in enumerate(original)
            if r.get("style_type") == "plain"
            and eligibility(r) == "eligible"
            and r.get("teacher_epistemic_vigilance") == "low"
            and r.get("evaluation_critic", {}).get("status") == "completed"
        ]
        rows = rows[: args.limit] if args.limit else rows
        target = (
            ROOT
            / "failure_mode"
            / ("pilot" if args.limit else "results")
            / model
            / stem
        )
        if args.dry_run:
            print(
                f"{model}: {stem}: {len(rows)} baseline failures, at most {5*len(rows)} calls; {target}"
            )
            continue
        provenance = dict(
            source=str(path.resolve()),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            critic_model="gpt-6-luna",
            prompt_sha256=hashlib.sha256(PROMPT.encode()).hexdigest(),
            limit=args.limit,
        )
        outcomes = [dict(status="pending") for _ in rows]
        checkpoint = target / "classifications.json"
        if checkpoint.exists():
            if not args.resume:
                raise ValueError("Output exists; use --resume")
            previous = json.loads(checkpoint.read_text())
            if previous["provenance"] != provenance or len(previous["records"]) != len(
                rows
            ):
                raise ValueError("Checkpoint input/prompt mismatch")
            outcomes = [r["review"] for r in previous["records"]]

        def persist():
            save(
                checkpoint,
                dict(
                    provenance=provenance,
                    records=[dict(**r, review=o) for r, o in zip(rows, outcomes)],
                ),
            )
            counts = Counter(
                o.get("classification", {}).get("assessment", o["status"])
                for o in outcomes
            )
            primary = Counter(
                o["classification"]["primary_category"]
                for o in outcomes
                if o.get("classification", {}).get("assessment") == "supported_failure"
            )
            secondary = Counter(
                c
                for o in outcomes
                for c in o.get("classification", {}).get("secondary_categories", [])
            )
            subtypes = Counter(
                c
                for o in outcomes
                for c in o.get("classification", {}).get(
                    "selective_verification_subtypes", []
                )
            )
            save(
                target / "summary.json",
                dict(
                    n_selected=len(rows),
                    assessment_counts=dict(counts),
                    primary_counts=dict(primary),
                    secondary_counts=dict(secondary),
                    subtype_counts=dict(subtypes),
                ),
            )
            lines = [
                f"# Baseline failure patterns: {model}",
                "",
                "Classifier: GPT Luna. Categories describe observed responses, not proven internal mechanisms.",
                f"Assessment counts: {dict(counts)}",
                f"Primary counts: {dict(primary)}",
                f"Secondary counts: {dict(secondary)}",
                f"Selective-verification subtype counts: {dict(subtypes)}",
                "",
                "| Source row | Subject | Session | Question | Assessment | Primary | Secondary | Subtypes | Confidence | Reasoning |",
                "|---:|---|---|---:|---|---|---|---|---|---|",
            ]
            flat = []
            for r, o in zip(rows, outcomes):
                c = o.get("classification", {})
                record = r["record"]
                item = dict(
                    source_index=r["source_index"],
                    subject=record.get("subject"),
                    session_id=record["session_id"],
                    question_turn_index=record["question_turn_index"],
                    assessment=c.get("assessment", o["status"]),
                    primary=c.get("primary_category"),
                    secondary="|".join(c.get("secondary_categories", [])),
                    subtypes="|".join(c.get("selective_verification_subtypes", [])),
                    confidence=c.get("confidence"),
                    reasoning=c.get("reasoning"),
                    evidence=json.dumps(c.get("evidence", [])),
                    attempts=o.get("attempts"),
                )
                flat.append(item)
                columns = list(item.values())[:10]
                lines.append(
                    "| "
                    + " | ".join(
                        str(v or "").replace("|", "\\|").replace("\n", " ")
                        for v in columns
                    )
                    + " |"
                )
            (target / "report.md").write_text("\n".join(lines) + "\n")
            if flat:
                with (target / "classifications.csv").open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
                    writer.writeheader()
                    writer.writerows(flat)

        persist()
        call = model_call("gpt-6-luna")
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(classify_record, r["record"], call): i
                for i, r in enumerate(rows)
                if outcomes[i]["status"] != "completed"
            }
            with tqdm(
                total=len(rows),
                initial=len(rows) - len(futures),
                desc=stem,
                unit="record",
                mininterval=5,
                disable=False,
            ) as progress:
                for future in as_completed(futures):
                    outcomes[futures[future]] = future.result()
                    persist()
                    progress.update(1)
                    progress.set_postfix(
                        errors=sum(o["status"] == "error" for o in outcomes),
                        refresh=False,
                    )
        any_errors |= any(o["status"] == "error" for o in outcomes)
        print(f"Saved {target}")
    if any_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
