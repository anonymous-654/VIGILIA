import argparse
from core.cli import positive_int
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

from tqdm import tqdm

from config import corruption_model_dir
from corruption.dialect.phenomena import (
    DEFAULT_DIALECT_PHENOMENA,
    DIALECT_PHENOMENA,
)
from core.checkpoints import prepare_checkpoint
from core.json_io import load_json, save_json
from corruption.dialect.dialect_phen_corruptor import (
    apply_dialect_phenomenon_corruption,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_corruptions_path", type=str, required=True)
    parser.add_argument("--model_path", type=str, required=True)
    parser.add_argument("--num_workers", type=positive_int, default=4)
    parser.add_argument("--limit", type=positive_int, default=None)
    parser.add_argument("--output_suffix", type=str, default=None)
    parser.add_argument(
        "--phenomena",
        nargs="*",
        default=DEFAULT_DIALECT_PHENOMENA,
        choices=sorted(DIALECT_PHENOMENA),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume only when inputs and generation settings match.",
    )
    return parser.parse_args()


def normalize_base_records(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list) and all("base_wrong_answer" in item for item in data):
        return data
    if isinstance(data, list) and all("base_corruptions" in item for item in data):
        records = []
        for group in data:
            records.extend(group["base_corruptions"])
        return records
    raise ValueError(
        "Expected flat base corruption records or grouped records containing "
        "base_corruptions."
    )


def process_one(
    model_path: str,
    base_record: Dict[str, Any],
    phenomenon_type: str,
) -> Dict[str, Any]:
    return apply_dialect_phenomenon_corruption(
        model_path=model_path,
        session_id=base_record["session_id"],
        question_turn_index=base_record["question_turn_index"],
        question_turn_number=base_record["question_turn_number"],
        question_text=base_record["question_text"],
        base_wrong_answer=base_record["base_wrong_answer"],
        phenomenon_type=phenomenon_type,
    ).model_dump()


def group_outputs(
    base_records: List[Dict[str, Any]],
    dialect_records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    base_by_session = defaultdict(list)
    dialect_by_session = defaultdict(list)

    for record in base_records:
        base_by_session[record["session_id"]].append(record)
    for record in dialect_records:
        dialect_by_session[record["session_id"]].append(record)

    grouped = []
    for session_id in sorted(base_by_session):
        base_items = sorted(
            base_by_session[session_id],
            key=lambda item: item["question_turn_index"],
        )
        all_dialect_items = sorted(
            dialect_by_session.get(session_id, []),
            key=lambda item: (item["question_turn_index"], item["phenomenon_type"]),
        )
        evaluator_items = [
            item
            for item in all_dialect_items
            if item["applicable"] and item["selected_item_validator_passed"]
        ]
        grouped.append(
            {
                "session_id": session_id,
                "num_base_corruptions": len(base_items),
                "num_dialect_phenomenon_corruptions": len(all_dialect_items),
                "num_applicable_dialect_phenomenon_corruptions": len(evaluator_items),
                "num_inapplicable_dialect_phenomenon_corruptions": (
                    len(all_dialect_items) - len(evaluator_items)
                ),
                "base_corruptions": base_items,
                "dialect_phenomenon_corruptions": all_dialect_items,
                # Compatibility with evaluate_language_phen_vigilance.py.
                "language_phenomenon_corruptions": evaluator_items,
            }
        )
    return grouped


def main():
    args = parse_args()
    base_records = normalize_base_records(load_json(Path(args.base_corruptions_path)))
    if args.limit is not None:
        base_records = base_records[: args.limit]

    stem = Path(args.base_corruptions_path).stem
    for suffix in ("_base_corruptions", "_grouped_corruptions"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    output_suffix = args.output_suffix
    if output_suffix is None and args.limit is not None:
        output_suffix = f"_sample{args.limit}"
    if output_suffix:
        stem += output_suffix

    out_dir = corruption_model_dir("dialect_phen", args.model_path)
    flat_path = out_dir / f"{stem}_dialect_phen_corruptions.json"
    grouped_path = out_dir / f"{stem}_dialect_phen_grouped_corruptions.json"
    checkpoint_path = out_dir / f"{stem}_dialect_phen_checkpoint.jsonl"

    prepare_checkpoint(
        out_dir / f"{stem}_dialect_phen.inputs.json",
        Path(args.base_corruptions_path),
        {"model": args.model_path, "conditions": args.phenomena, "limit": args.limit},
        [flat_path, grouped_path, checkpoint_path],
        args.resume,
    )

    def task_key(record: Dict[str, Any]) -> tuple:
        return (
            record["session_id"],
            record["question_turn_index"],
            record["phenomenon_type"],
        )

    outputs_by_key = {}
    if flat_path.exists():
        for record in load_json(flat_path):
            outputs_by_key[task_key(record)] = record
    if checkpoint_path.exists():
        with checkpoint_path.open("r", encoding="utf-8") as checkpoint_file:
            for line_number, line in enumerate(checkpoint_file, start=1):
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    print(
                        f"[WARNING] Ignoring incomplete checkpoint line "
                        f"{line_number} in {checkpoint_path}"
                    )
                    continue
                outputs_by_key[task_key(record)] = record

    tasks = [
        (base_record, phenomenon_type)
        for base_record in base_records
        for phenomenon_type in args.phenomena
        if (
            base_record["session_id"],
            base_record["question_turn_index"],
            phenomenon_type,
        )
        not in outputs_by_key
    ]
    num_errors = 0
    print(
        f"Resuming with {len(outputs_by_key)} completed records; "
        f"{len(tasks)} tasks remain"
    )

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        checkpoint_path.open("a", encoding="utf-8") as checkpoint_file,
        ThreadPoolExecutor(max_workers=args.num_workers) as executor,
    ):
        future_to_task = {
            executor.submit(
                process_one, args.model_path, base_record, phenomenon_type
            ): (
                base_record,
                phenomenon_type,
            )
            for base_record, phenomenon_type in tasks
        }
        for future in tqdm(
            as_completed(future_to_task),
            total=len(future_to_task),
            desc="dialect phenomena",
        ):
            base_record, phenomenon_type = future_to_task[future]
            try:
                record = future.result()
                outputs_by_key[task_key(record)] = record
                checkpoint_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                checkpoint_file.flush()
            except Exception as exc:
                num_errors += 1
                print(
                    f"[ERROR] session_id={base_record.get('session_id')} "
                    f"q_idx={base_record.get('question_turn_index')} "
                    f"phenomenon={phenomenon_type} error={exc!r}"
                )

    outputs = list(outputs_by_key.values())
    save_json(flat_path, outputs)
    save_json(grouped_path, group_outputs(base_records, outputs))

    applicable = sum(
        1
        for item in outputs
        if item["applicable"] and item["selected_item_validator_passed"]
    )
    print(f"Saved flat dialect phenomenon corruptions to: {flat_path}")
    print(f"Saved grouped dialect phenomenon corruptions to: {grouped_path}")
    print(
        f"Completed: {len(outputs)} records, {applicable} evaluator-ready, "
        f"{num_errors} failed"
    )

    if num_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
