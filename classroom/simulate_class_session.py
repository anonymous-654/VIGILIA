import argparse
from core.cli import positive_int
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple

from tqdm import tqdm

from classroom.simulation import run_class_session
from config import safe_model_name, simulation_model_dir
from subjects import COURSE_SUBJECTS
from classroom.roster import STUDENTS


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", type=str, required=True)
    parser.add_argument("--num_runs", type=positive_int, required=True)
    parser.add_argument("--num_raisers", type=positive_int, default=2)
    parser.add_argument("--max_turns", type=positive_int, default=200)
    parser.add_argument("--num_workers", type=positive_int, default=6)
    parser.add_argument(
        "--out_dir",
        type=str,
        default=None,
        help="Optional raw-session output dir. Defaults to data/simulations/{model_name}/raw_sessions.",
    )
    parser.add_argument(
        "--session_indices",
        type=str,
        default=None,
        help="Optional comma-separated session indices to run, e.g. 72,73,74.",
    )
    parser.add_argument(
        "--output_suffix",
        type=str,
        default=None,
        help="Optional suffix for the merged summary filename.",
    )
    return parser.parse_args()


def parse_session_indices(session_indices: Optional[str], num_runs: int) -> List[int]:
    if not session_indices:
        return list(range(num_runs))

    indices = []
    for raw_idx in session_indices.split(","):
        raw_idx = raw_idx.strip()
        if not raw_idx:
            continue
        idx = int(raw_idx)
        if idx < 0:
            raise ValueError(f"Session index must be non-negative: {idx}")
        indices.append(idx)

    if not indices:
        raise ValueError("--session_indices was provided but no indices were parsed.")

    if len(set(indices)) != len(indices):
        raise ValueError("Session indices must be unique")
    return indices


def build_session_pairs() -> List[Tuple[str, str]]:
    return [
        (subj, topic) for subj, topics in COURSE_SUBJECTS.items() for topic in topics
    ]


def run_one_session(
    session_idx: int,
    students: List[Dict[str, Any]],
    model_path: str,
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
    num_raisers: int,
    num_runs: int,
    max_turns: int,
    output_dir: Path,
    output_suffix: Optional[str] = None,
) -> Path:
    model_name = safe_model_name(model_path)
    suffix = f"_{output_suffix}" if output_suffix else ""
    merged_path = output_dir / (
        f"sessions_summary_{model_name}_{num_raisers}_{num_runs}_{max_turns}{suffix}.json"
    )

    merged_results = []

    for path in session_paths:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)

        d.setdefault("metadata", {})
        d["metadata"].setdefault("merged_from", str(path))
        d["metadata"].setdefault("model_path", model_path)
        d["metadata"].setdefault("num_raisers", num_raisers)
        d["metadata"].setdefault("num_runs", num_runs)
        d["metadata"].setdefault("max_turns", max_turns)

        merged_results.append(d)

    with open(merged_path, "w", encoding="utf-8") as f:
        json.dump(merged_results, f, ensure_ascii=False, indent=2)

    return merged_path


def main():
    args = parse_args()
    students = [dict(student) for student in STUDENTS]
    run_dir = simulation_model_dir(args.model_path)
    out_dir = Path(args.out_dir) if args.out_dir else run_dir / "raw_sessions"
    out_dir.mkdir(parents=True, exist_ok=True)
    session_indices = parse_session_indices(args.session_indices, args.num_runs)
    output_suffix = args.output_suffix
    if args.session_indices and not output_suffix:
        output_suffix = "selected_sessions"

    total_prompt_tokens = 0
    total_completion_tokens = 0
    bad_turns = 0
    failures = 0

    created_session_paths = []

    futures = []
    with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        for session_idx in session_indices:
            futures.append(
                executor.submit(
                    run_one_session,
                    session_idx,
                    students,
                    args.model_path,
                    args.num_raisers,
                    args.max_turns,
                    out_dir,
                )
            )

        for fut in tqdm(as_completed(futures), total=len(futures), desc="Sessions"):
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
                print(
                    f"[OK] session={result['session_idx']} saved={result['out_path']}"
                )

    merged_path = merge_session_summaries(
        session_paths=created_session_paths,
        model_path=args.model_path,
        num_raisers=args.num_raisers,
        num_runs=args.num_runs,
        max_turns=args.max_turns,
        output_dir=run_dir,
        output_suffix=output_suffix,
    )

    print(f"==== Sessions merged this run == {len(created_session_paths)} =====")
    print(f"==== Total Prompt Tokens == {total_prompt_tokens} =====")
    print(f"==== Total Completion Tokens == {total_completion_tokens} =====")
    print(f"==== Total Number of bad turns == {bad_turns} =====")
    print(f"==== Total Failures == {failures} =====")
    print(f"==== Merged summary saved to == {merged_path} =====")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
