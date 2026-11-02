import argparse
from vigilance.validity import invalid_reason
from core.cli import positive_int
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from config import evaluation_model_dir
from vigilance.baseline import load_baselines, baseline_for, stamp_output
from vigilance.evaluation import evaluate_single_styled_answer
from core.json_io import load_json, save_json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_path", type=str, required=True)
    parser.add_argument("--grouped_corruptions_path", type=str, required=True)
    parser.add_argument("--num_workers", type=positive_int, default=4)
    parser.add_argument(
        "--reuse_cached_baselines",
        action="store_true",
        help="Explicitly reuse historical successful baselines with matching session and canonical inputs.",
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


def evaluate_one_item(session_id, session, styled):
    try:
        result = evaluate_single_styled_answer(session, styled)
        return {
            "ok": True,
            "result": result.model_dump(),
            "session_id": session_id,
            "question_turn_index": styled.get("question_turn_index"),
            "style_type": styled.get("style_type"),
        }
    except Exception as e:
        return {
            "ok": False,
            "error": repr(e),
            "session_id": session_id,
            "question_turn_index": styled.get("question_turn_index"),
            "style_type": styled.get("style_type"),
        }


def main():
    args = parse_args()
    if args.reuse_cached_baselines:
        os.environ["VIGILANCE_REUSE_CACHED_BASELINES"] = "1"
        print(
            "Reusing historical baselines with matching inputs; their original settings remain recorded.",
            flush=True,
        )

    session_data = load_json(Path(args.session_path))
    sessions = normalize_sessions(session_data)
    session_map = {s["session_id"]: s for s in sessions}
    if len(session_map) != len(sessions):
        raise ValueError("Session IDs must be unique")
    if len({s.get("metadata", {}).get("model_path") for s in sessions}) != 1:
        raise ValueError("Evaluation requires sessions from one teacher model")

    grouped = load_json(Path(args.grouped_corruptions_path))

    shared = load_baselines(
        args.session_path, args.grouped_corruptions_path, create=True
    )
    outputs = []
    tasks = []
    for group in grouped:
        session_id = group["session_id"]
        session = session_map.get(session_id)

        if session is None:
            raise ValueError(f"Missing session for {session_id}")

        for base in group.get("base_corruptions", []):
            outputs.append(baseline_for(base, shared))
        for styled in group["styled_corruptions"]:
            if styled["style_type"] != "plain":
                tasks.append((session_id, session, styled))

    num_errors = 0

    with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        futures = [
            executor.submit(evaluate_one_item, session_id, session, styled)
            for session_id, session, styled in tasks
        ]

        for fut in tqdm(
            as_completed(futures), total=len(futures), desc="evaluating vigilance"
        ):
            item = fut.result()
            if item["ok"]:
                outputs.append(item["result"])
            else:
                num_errors += 1
                print(
                    f"[ERROR] session_id={item['session_id']} "
                    f"q_idx={item['question_turn_index']} "
                    f"style={item['style_type']} "
                    f"error={item['error']}"
                )

    stem = Path(args.session_path).stem
    out_dir = evaluation_model_dir("main", session_model_path(sessions))
    out_path = out_dir / f"{stem}_vigilance_eval.json"

    save_json(out_path, outputs)
    stamp_output(
        out_path,
        args.session_path,
        args.grouped_corruptions_path,
        args.grouped_corruptions_path,
    )
    print(f"Saved: {out_path}")
    print(f"Completed: {len(outputs)} successful, {num_errors} failed")

    if num_errors or any(invalid_reason(row) for row in outputs):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
