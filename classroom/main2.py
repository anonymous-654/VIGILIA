import argparse
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple

from tqdm import tqdm

from classroom.session import run_class_session
from subjects import COURSE_SUBJECTS
from profiles import PROFILES


RAW_SESSION_DIR = Path("raw_sessions")
RAW_SESSION_DIR.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", type=str, required=True)
    parser.add_argument("--num_runs", type=int, required=True)
    parser.add_argument("--profile_type", type=str, required=True)
    parser.add_argument("--eval_type", type=str, default="fairness")
    parser.add_argument("--num_raisers", type=int, default=2)
    parser.add_argument("--max_turns", type=int, default=200)
    parser.add_argument("--num_workers", type=int, default=4)
    parser.add_argument("--out_dir", type=str, default="raw_sessions")
    return parser.parse_args()


def get_students(profile_type: str):
    return PROFILES[profile_type]


def build_session_pairs() -> List[Tuple[str, str]]:
    return [(subj, topic) for subj, topics in COURSE_SUBJECTS.items() for topic in topics]


def run_one_session(
    session_idx: int,
    students: List[Dict[str, Any]],
    model_path: str,
    profile_type: str,
    num_raisers: int,
    max_turns: int,
    out_dir: Path,
) -> Dict[str, Any]:
    session_pairs = build_session_pairs()
    subject, topic = session_pairs[session_idx % len(session_pairs)]

    try:
        record = run_class_session(
            students=students,
            model_path=model_path,
            subject=subject,
            topic=topic,
            profile_type=profile_type,
            num_raisers=num_raisers,
            max_turns=max_turns,
        )

        d = record.model_dump()
        d.setdefault("metadata", {})
        d["metadata"]["model_path"] = model_path
        d["metadata"]["session_index"] = session_idx
        d["metadata"]["subject"] = subject
        d["metadata"]["topic"] = topic

        turns_ran = d.get("turns_ran", 0)
        is_bad = turns_ran >= max_turns

        out_path = out_dir / f"session_{session_idx}_{record.session_id}.json"
        save_json(out_path, d)

        return {
            "ok": True,
            "session_idx": session_idx,
            "subject": subject,
            "topic": topic,
            "out_path": str(out_path),
            "prompt_tokens": d.get("prompt_tokens", 0),
            "completion_tokens": d.get("completion_tokens", 0),
            "turns_ran": turns_ran,
            "bad_turn": is_bad,
        }

    except Exception as e:
        return {
            "ok": False,
            "session_idx": session_idx,
            "subject": subject,
            "topic": topic,
            "error": str(e),
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "bad_turn": False,
        }


def merge_session_summaries(
    session_paths: List[Path],
    model_path: str,
    profile_type: str,
    eval_type: str,
    num_raisers: int,
    num_runs: int,
    max_turns: int,
) -> Path:
    safe_model_name = model_path.replace("/", "_")
    merged_path = Path(
        f"sessions_summary_{safe_model_name}_{profile_type}_{eval_type}_{num_raisers}_{num_runs}_{max_turns}.json"
    )

    merged_results = []

    for path in session_paths:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)

        d.setdefault("metadata", {})
        d["metadata"].setdefault("merged_from", str(path))
        d["metadata"].setdefault("model_path", model_path)
        d["metadata"].setdefault("profile_type", profile_type)
        d["metadata"].setdefault("eval_type", eval_type)
        d["metadata"].setdefault("num_raisers", num_raisers)
        d["metadata"].setdefault("num_runs", num_runs)
        d["metadata"].setdefault("max_turns", max_turns)

        merged_results.append(d)

    with open(merged_path, "w", encoding="utf-8") as f:
        json.dump(merged_results, f, ensure_ascii=False, indent=2)

    return merged_path


def main():
    args = parse_args()
    students = get_students(args.profile_type)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    total_prompt_tokens = 0
    total_completion_tokens = 0
    bad_turns = 0
    failures = 0

    created_session_paths = []

    futures = []
    with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        for session_idx in range(args.num_runs):
            futures.append(
                executor.submit(
                    run_one_session,
                    session_idx,
                    students,
                    args.model_path,
                    args.profile_type,
                    args.num_raisers,
                    args.max_turns,
                    out_dir,
                )
            )

        for fut in tqdm(as_completed(futures), total=len(futures), desc=f"Sessions[{args.profile_type}]"):
            result = fut.result()

            total_prompt_tokens += result.get("prompt_tokens", 0)
            total_completion_tokens += result.get("completion_tokens", 0)

            if not result["ok"]:
                failures += 1
                print(
                    f"[ERROR] session={result['session_idx']} "
                    f"subject={result['subject']} topic={result['topic']} "
                    f"error={result['error']}"
                )
                continue

            created_session_paths.append(Path(result["out_path"])) 

            if result["bad_turn"]:
                bad_turns += 1
                print(
                    f"[BAD SESSION] session={result['session_idx']} "
                    f"turns_ran={result['turns_ran']} "
                    f"saved={result['out_path']}"
                )
            else:
                print(f"[OK] session={result['session_idx']} saved={result['out_path']}")

    merged_path = merge_session_summaries(
        session_paths=created_session_paths,
        model_path=args.model_path,
        profile_type=args.profile_type,
        eval_type=args.eval_type,
        num_raisers=args.num_raisers,
        num_runs=args.num_runs,
        max_turns=args.max_turns,
    )

    print(f"==== Sessions merged this run == {len(created_session_paths)} =====")
    print(f"==== Total Prompt Tokens == {total_prompt_tokens} =====")
    print(f"==== Total Completion Tokens == {total_completion_tokens} =====")
    print(f"==== Total Number of bad turns == {bad_turns} =====")
    print(f"==== Total Failures == {failures} =====")
    print(f"==== Merged summary saved to == {merged_path} =====")


if __name__ == "__main__":
    main()