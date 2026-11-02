import argparse
from core.cli import positive_int
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

from tqdm import tqdm

from config import corruption_model_dir
from core.json_io import load_json, save_json
from core.language_phen import DEFAULT_LANGUAGE_PHENOMENA, LANGUAGE_PHENOMENA
from corruption.language_phen_corruptor import (
    apply_language_phenomenon_corruption,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_corruptions_path", type=str, required=True)
    parser.add_argument("--model_path", type=str, required=True)
    parser.add_argument("--num_workers", type=positive_int, default=4)
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=None,
        help="Optional number of base corruption records to process for a small inspection run.",
    )
    parser.add_argument(
        "--output_suffix",
        type=str,
        default=None,
        help="Optional suffix added to output filenames before _language_phen_corruptions.",
    )
    parser.add_argument(
        "--phenomena",
        nargs="*",
        default=DEFAULT_LANGUAGE_PHENOMENA,
        choices=sorted(LANGUAGE_PHENOMENA.keys()),
    )
    parser.add_argument(
        "--degree",
        type=int,
        choices=[1, 2, 3],
        default=1,
        help="Strength of language phenomenon injection passed to the prompt.",
    )
    return parser.parse_args()


def normalize_base_records(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list) and all("base_wrong_answer" in x for x in data):
        return data

    if isinstance(data, list) and all("base_corruptions" in x for x in data):
        records: List[Dict[str, Any]] = []
        for group in data:
            records.extend(group["base_corruptions"])
        return records

    raise ValueError(
        "Unsupported base corruption format. Expected a flat base corruption file "
        "or a grouped corruption file containing base_corruptions."
    )


def process_one_phenomenon(
    model_path: str,
    base_record: Dict[str, Any],
    phenomenon_type: str,
    degree: int,
) -> Dict[str, Any]:
    record = apply_language_phenomenon_corruption(
        model_path=model_path,
        session_id=base_record["session_id"],
        question_turn_index=base_record["question_turn_index"],
        question_turn_number=base_record["question_turn_number"],
        question_text=base_record["question_text"],
        base_wrong_answer=base_record["base_wrong_answer"],
        phenomenon_type=phenomenon_type,
        degree=degree,
    )
    return record.model_dump()


def group_outputs(base_records, phenomenon_records):
    base_by_session = defaultdict(list)
    phen_by_session = defaultdict(list)
    for record in base_records:
        base_by_session[record["session_id"]].append(record)
    for record in phenomenon_records:
        phen_by_session[record["session_id"]].append(record)
    grouped = []
    for session_id in sorted(base_by_session):
        base_items = sorted(
            base_by_session[session_id], key=lambda x: x["question_turn_index"]
        )
        phen_items = sorted(
            phen_by_session[session_id],
            key=lambda x: (x["question_turn_index"], x["phenomenon_type"]),
        )
        grouped.append(
            dict(
                session_id=session_id,
                num_base_corruptions=len(base_items),
                num_language_phenomenon_corruptions=len(phen_items),
                base_corruptions=base_items,
                language_phenomenon_corruptions=phen_items,
            )
        )
    return grouped


def main():
    args = parse_args()
    data = load_json(Path(args.base_corruptions_path))
    base_records = normalize_base_records(data)
    if args.limit is not None:
        base_records = base_records[: args.limit]

    tasks = [
        (base_record, phenomenon_type)
        for base_record in base_records
        for phenomenon_type in args.phenomena
    ]

    outputs: List[Dict[str, Any]] = []
    num_errors = 0

    with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        future_to_task = {
            executor.submit(
                process_one_phenomenon,
                args.model_path,
                base_record,
                phenomenon_type,
                args.degree,
            ): (
                base_record,
                phenomenon_type,
            )
            for base_record, phenomenon_type in tasks
        }

        for fut in tqdm(
            as_completed(future_to_task),
            total=len(future_to_task),
            desc="language phenomena",
        ):
            base_record, phenomenon_type = future_to_task[fut]
            try:
                record = fut.result()
                outputs.append(record)
            except Exception as e:
                num_errors += 1
                print(
                    f"[ERROR] session_id={base_record.get('session_id')} "
                    f"q_idx={base_record.get('question_turn_index')} "
                    f"phenomenon={phenomenon_type} error={repr(e)}"
                )

    stem = Path(args.base_corruptions_path).stem
    if stem.endswith("_base_corruptions"):
        stem = stem[: -len("_base_corruptions")]
    elif stem.endswith("_grouped_corruptions"):
        stem = stem[: -len("_grouped_corruptions")]

    output_suffix = args.output_suffix
    if output_suffix is None and args.limit is not None:
        output_suffix = f"_sample{args.limit}"
    if output_suffix:
        stem = f"{stem}{output_suffix}"
    stem = f"{stem}_degree{args.degree}"

    grouped = group_outputs(base_records, outputs)
    all_outputs = outputs

    out_dir = corruption_model_dir("phen", args.model_path)
    flat_path = out_dir / f"{stem}_language_phen_corruptions.json"
    grouped_path = out_dir / f"{stem}_language_phen_grouped_corruptions.json"

    save_json(flat_path, all_outputs)
    save_json(grouped_path, grouped)

    print(f"Saved flat language phenomenon corruptions to: {flat_path}")
    print(f"Saved grouped language phenomenon corruptions to: {grouped_path}")
    print("Completed: " f"{len(outputs)} successful, {num_errors} failed")

    if num_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
