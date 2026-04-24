import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from config import EVAL_DIR
from vigilance.stats_utils import compute_vigilance_stats
from vigilance.vigilance import evaluate_single_styled_answer
from store_utils import load_json, save_json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_path", type=str, required=True)
    parser.add_argument("--grouped_corruptions_path", type=str, required=True)
    parser.add_argument("--num_workers", type=int, default=4)
    return parser.parse_args()


def normalize_sessions(data):
    if isinstance(data, list):
        return data
    return [data]


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

    session_data = load_json(Path(args.session_path))
    sessions = normalize_sessions(session_data)
    session_map = {s["session_id"]: s for s in sessions}

    grouped = load_json(Path(args.grouped_corruptions_path))

    tasks = []
    for group in grouped:
        session_id = group["session_id"]
        session = session_map.get(session_id)

        if session is None:
            print(f"[ERROR] missing session for {session_id}")
            continue

        for styled in group["styled_corruptions"]:
            tasks.append((session_id, session, styled))

    outputs = []
    num_errors = 0

    with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        futures = [
            executor.submit(evaluate_one_item, session_id, session, styled)
            for session_id, session, styled in tasks
        ]

        for fut in tqdm(as_completed(futures), total=len(futures), desc="evaluating vigilance"):
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
    out_path = EVAL_DIR / f"{stem}_vigilance_eval.json"

    stats = compute_vigilance_stats(outputs)
    print(stats)

    save_json(out_path, outputs)
    print(f"Saved: {out_path}")
    print(f"Completed: {len(outputs)} successful, {num_errors} failed")


if __name__ == "__main__":
    main()