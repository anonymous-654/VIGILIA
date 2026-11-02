import argparse
from core.cli import positive_int
from vigilance.validity import invalid_reason
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

from config import evaluation_model_dir
from core.json_io import load_json, save_json
from vigilance.baseline import load_baselines, baseline_for, stamp_output
from vigilance.evaluation import evaluate_single_language_phenomenon_answer


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_path", type=str, required=True)
    parser.add_argument("--grouped_corruptions_path", type=str, required=True)
    parser.add_argument(
        "--canonical_corruptions_path",
        help="Main grouped corruptions used to create shared baselines.",
    )
    parser.add_argument("--num_workers", type=positive_int, default=4)
    parser.add_argument(
        "--no_baseline",
        action="store_true",
        help="Do not evaluate the original base wrong answer as phenomenon_type=baseline.",
    )
    return parser.parse_args()


def normalize_sessions(data):
    if isinstance(data, list):
        return data
    return [data]


def session_model_path(sessions):
    if not sessions:
        raise ValueError("Cannot infer model path from an empty session file.")
    metadata = sessions[0].get("metadata", {})
    model_path = metadata.get("model_path")
    if not model_path:
        raise ValueError(
            "Cannot infer model path; session metadata is missing model_path."
        )
    return model_path


def resolve_output_path(
    session_path: str, grouped_corruptions_path: str, model_path: str
) -> Path:
    grouped_stem = Path(grouped_corruptions_path).stem
    for family in ("dialect_speaker", "dialect_phen", "language_phen"):
        suffix = f"_{family}_grouped_corruptions"
        if grouped_stem.endswith(suffix):
            stem = grouped_stem[: -len("_grouped_corruptions")]
            return (
                evaluation_model_dir(family, model_path) / f"{stem}_vigilance_eval.json"
            )
    raise ValueError(
        "Grouped filename must identify language_phen, dialect_phen or dialect_speaker"
    )


def evaluate_one_item(session_id, session, phenomenon_record):
    try:
        result = evaluate_single_language_phenomenon_answer(session, phenomenon_record)
        return {
            "ok": True,
            "result": result.model_dump(),
            "session_id": session_id,
            "question_turn_index": phenomenon_record.get("question_turn_index"),
            "phenomenon_type": phenomenon_record.get("phenomenon_type"),
        }
    except Exception as e:
        return {
            "ok": False,
            "error": repr(e),
            "session_id": session_id,
            "question_turn_index": phenomenon_record.get("question_turn_index"),
            "phenomenon_type": phenomenon_record.get("phenomenon_type"),
        }


def main():
    args = parse_args()

    session_data = load_json(Path(args.session_path))
    sessions = normalize_sessions(session_data)
    session_map = {s["session_id"]: s for s in sessions}
    if len(session_map) != len(sessions):
        raise ValueError("Session IDs must be unique")
    if len({s.get("metadata", {}).get("model_path") for s in sessions}) != 1:
        raise ValueError("Evaluation requires sessions from one teacher model")

    grouped = load_json(Path(args.grouped_corruptions_path))

    if not args.no_baseline and not args.canonical_corruptions_path:
        raise ValueError(
            "Pass --canonical_corruptions_path and run main evaluation first to populate shared baselines."
        )
    shared = (
        load_baselines(args.session_path, args.canonical_corruptions_path)
        if not args.no_baseline
        else {}
    )
    outputs = []
    tasks = []
    for group in grouped:
        session_id = group["session_id"]
        session = session_map.get(session_id)

        if session is None:
            raise ValueError(f"Missing session for {session_id}")

        if not args.no_baseline:
            for base_record in group.get("base_corruptions", []):
                outputs.append(baseline_for(base_record, shared, phenomenon=True))

        for phenomenon_record in group["language_phenomenon_corruptions"]:
            tasks.append((session_id, session, phenomenon_record))

    num_errors = 0

    with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        futures = [
            executor.submit(evaluate_one_item, session_id, session, phenomenon_record)
            for session_id, session, phenomenon_record in tasks
        ]

        for fut in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="evaluating language phenomenon vigilance",
        ):
            item = fut.result()
            if item["ok"]:
                outputs.append(item["result"])
            else:
                num_errors += 1
                print(
                    f"[ERROR] session_id={item['session_id']} "
                    f"q_idx={item['question_turn_index']} "
                    f"phenomenon={item['phenomenon_type']} "
                    f"error={item['error']}"
                )

    out_path = resolve_output_path(
        session_path=args.session_path,
        grouped_corruptions_path=args.grouped_corruptions_path,
        model_path=session_model_path(sessions),
    )

    save_json(out_path, outputs)
    if not args.no_baseline:
        stamp_output(
            out_path,
            args.session_path,
            args.grouped_corruptions_path,
            args.canonical_corruptions_path,
        )
    print(f"Saved: {out_path}")
    print(f"Completed: {len(outputs)} successful, {num_errors} failed")

    if num_errors or any(invalid_reason(row) for row in outputs):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
