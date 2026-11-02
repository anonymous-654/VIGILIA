"""Two-stage critic runner; all outputs stay inside evaluation_critic/."""

import argparse
import hashlib
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm
from tempfile import NamedTemporaryFile
from config import EVAL_DIR
from evaluation_critic.prompts import VERSION, ANSWER, TEACHER
from evaluation_critic.review import review_record, apply_review, model_call

ROOT = Path(__file__).resolve().parents[1]


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", dir=str(path.parent), delete=False) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = handle.name
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Teacher model/directory key")
    parser.add_argument("--critic-model", default="gpt-6-luna")
    parser.add_argument(
        "--input",
        type=Path,
        help="Review a specific evaluation JSON instead of discovery",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--limit", type=int, help="Pilot: review only the first N records"
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or (args.limit is not None and args.limit < 1):
        parser.error("Workers and limit must be positive")
    model = args.model.replace("/", "_")
    if model in {"", ".", ".."} or "\\" in model:
        parser.error("Invalid model key")
    inputs = (
        [args.input]
        if args.input
        else [
            p
            for family in ("main", "language_phen", "dialect_phen", "dialect_speaker")
            for p in sorted((EVAL_DIR / family / model).glob("*_vigilance_eval.json"))
            if "_replayed_" not in p.name
        ]
    )
    if not inputs:
        parser.error("No evaluation files found")
    failed = False
    for path in inputs:
        rows = json.loads(path.read_text())
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            raise ValueError("Input must be an array of evaluation records")
        if any("evaluation_critic" in r for r in rows):
            raise ValueError("Use original evaluations as input")
        rows = rows[: args.limit] if args.limit else rows
        # Pilot artifacts remain separate from full outputs.
        folder = (
            ROOT
            / "evaluation_critic"
            / ("pilot" if args.limit else "results")
            / model
            / path.stem
        )
        if args.critic_model != "gpt-6-luna":
            folder = folder / args.critic_model.replace("/", "_")
        checkpoint = folder / "audit.json"
        provenance = dict(
            input=str(path.resolve()),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            critic_model=args.critic_model,
            scope="original_answer_eval_INCORRECT",
            prompt_version=VERSION,
            prompt_sha256=hashlib.sha256((ANSWER + TEACHER).encode()).hexdigest(),
            limit=args.limit,
        )
        if args.dry_run:
            selected = sum(
                str(r.get("answer_eval", "")).strip().upper() == "INCORRECT"
                for r in rows
            )
            print(
                f"{path}: {selected}/{len(rows)} records selected, at most {10*selected} calls (including retries) to {args.critic_model}; output {folder}"
            )
            continue
        audit = [
            (
                dict(status="pending")
                if str(r.get("answer_eval", "")).strip().upper() == "INCORRECT"
                else dict(
                    status="skipped", reason="Original answer_eval is not INCORRECT"
                )
            )
            for r in rows
        ]
        if checkpoint.exists():
            if not args.resume:
                raise ValueError(f"{checkpoint} exists; use --resume")
            saved = json.loads(checkpoint.read_text())
            if saved["provenance"] != provenance or len(saved["records"]) != len(rows):
                raise ValueError("Checkpoint input/model/prompts differ")
            audit = saved["records"]
        call = model_call(args.critic_model)

        def persist():
            save(checkpoint, dict(provenance=provenance, records=audit))
            save(
                folder / "reviewed_evaluations.json",
                [apply_review(r, a) for r, a in zip(rows, audit)],
            )
            counts = Counter(a["status"] for a in audit)
            decisions = {
                stage: dict(
                    Counter(
                        a.get(stage, {}).get("decision", "not reviewed") for a in audit
                    )
                )
                for stage in ("answer", "teacher")
            }
            lines = [
                "# Two-stage evaluation critic",
                "",
                f"Input: `{path}`",
                f"Critic: `{args.critic_model}`",
                "",
                "Source evaluations are unchanged. Revisions are model judgments, not verified ground truth.",
                "Unresolved records are marked invalid in the derived evaluation file.",
                "",
                f"Status counts: {dict(counts)}",
                f"Decisions: {decisions}",
                "",
                "| Row (0-based) | Session | Question | Stage | Decision/status | Proposed labels | Reasoning |",
                "|---:|---|---:|---|---|---|---|",
            ]
            for i, (row, item) in enumerate(zip(rows, audit)):
                for stage in ("answer", "teacher"):
                    review = item.get(stage, {})
                    if item["status"] == "skipped" or (
                        review.get("decision") == "agree"
                        and item["status"] == "completed"
                    ):
                        continue

                    def safe(value):
                        return str(value).replace("|", "\\|").replace("\n", " ")

                    labels = (
                        review.get("verdict")
                        if stage == "answer"
                        else (
                            review.get("teacher_epistemic_vigilance"),
                            review.get("teacher_action_evaluated"),
                        )
                    )
                    lines.append(
                        f"| {i} | {row.get('session_id')} | {row.get('question_turn_index')} | {stage} | {review.get('decision', item['status'])} | {safe(labels)} | {safe(review.get('reasoning', item.get('error', review.get('reason', ''))))} |"
                    )
            (folder / "report.md").write_text("\n".join(lines) + "\n")

        persist()
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(review_record, row, call, audit[i]): i
                for i, row in enumerate(rows)
                if audit[i]["status"] not in {"completed", "needs_review", "skipped"}
            }
            selected = [
                i for i, item in enumerate(audit) if item["status"] != "skipped"
            ]
            initial = len(selected) - len(futures)
            # Explicitly enabled for Slurm logs; each update is one finished record,
            # including any internal retries. Resumed completed reviews count initially.
            with tqdm(
                total=len(selected),
                initial=initial,
                desc=path.stem,
                unit="record",
                mininterval=5,
                disable=False,
                dynamic_ncols=False,
            ) as progress:
                for future in as_completed(futures):
                    i = futures[future]
                    audit[i] = future.result()
                    persist()
                    counts = Counter(audit[j]["status"] for j in selected)
                    progress.set_postfix(
                        completed=counts["completed"],
                        errors=counts["error"],
                        uncertain=counts["needs_review"],
                        refresh=False,
                    )
                    progress.update(1)
        failed |= any(a["status"] == "error" for a in audit)
        print(f"Saved {folder}", flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
