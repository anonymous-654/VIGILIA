import argparse
from core.cli import positive_int
from pathlib import Path
from typing import Any, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from config import DEFAULT_STYLE_TYPES, corruption_model_dir
from corruption.base_corruptor import generate_base_corruption
from corruption.claims import extract_claims
from corruption.gold import extract_question_gold_records
from corruption.selector import choose_claim_and_error_type
from corruption.style_corruptor import apply_style_corruption
from core.checkpoints import prepare_checkpoint
from core.json_io import load_json, save_json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_path", type=str, required=True)
    parser.add_argument("--model_path", type=str, required=True)
    parser.add_argument("--session_workers", type=positive_int, default=6)
    parser.add_argument("--style_workers", type=positive_int, default=4)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse saved sessions and process only missing session IDs.",
    )
    return parser.parse_args()


def normalize_sessions(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError(f"Unsupported session file format: {type(data)}")


def process_one_style(
    model_path: str,
    record,
    base_wrong_answer: str,
    style_type: str,
) -> Dict[str, Any]:
    styled = apply_style_corruption(
        model_path=model_path,
        session_id=record.session_id,
        question_turn_index=record.question_turn_index,
        question_turn_number=record.question_turn_number,
        question_text=record.question_text,
        base_wrong_answer=base_wrong_answer,
        style_type=style_type,
    )
    return styled.model_dump()


def process_one_question(
    record,
    model_path: str,
    style_workers: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    claims = extract_claims(record.question_text, record.gold_answer)
    record.claims = claims

    claim_id, error_type, reason = choose_claim_and_error_type(
        record.question_text,
        record.gold_answer,
        claims,
    )

    base = generate_base_corruption(
        model_path=model_path,
        session_id=record.session_id,
        question_turn_index=record.question_turn_index,
        question_turn_number=record.question_turn_number,
        question_text=record.question_text,
        gold_answer=record.gold_answer,
        claims=claims,
        selected_claim_id=claim_id,
        selected_error_type=error_type,
        selection_reason=reason,
    )
    base_dict = base.model_dump()

    styled_records: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=style_workers) as executor:
        futures = [
            executor.submit(
                process_one_style,
                model_path,
                record,
                base.base_wrong_answer,
                style,
            )
            for style in DEFAULT_STYLE_TYPES
        ]

        for fut in as_completed(futures):
            styled_records.append(fut.result())

    return base_dict, styled_records


def process_one_session(
    session: Dict[str, Any],
    model_path: str,
    style_workers: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    gold_records = extract_question_gold_records(session)

    session_base_records: List[Dict[str, Any]] = []
    session_styled_records: List[Dict[str, Any]] = []

    for record in gold_records:
        base_dict, styled_dicts = process_one_question(
            record=record,
            model_path=model_path,
            style_workers=style_workers,
        )
        session_base_records.append(base_dict)
        session_styled_records.extend(styled_dicts)

    grouped = {
        "session_id": session.get("session_id"),
        "session_index": session.get(
            "session_index", session.get("metadata", {}).get("session_index")
        ),
        "subject": session.get("subject"),
        "topic": session.get("topic"),
        "num_base_corruptions": len(session_base_records),
        "num_styled_corruptions": len(session_styled_records),
        "base_corruptions": session_base_records,
        "styled_corruptions": session_styled_records,
    }

    return session_base_records, session_styled_records, grouped


def main():
    args = parse_args()
    data = load_json(Path(args.session_path))
    sessions = normalize_sessions(data)
    session_ids = [session.get("session_id") for session in sessions]
    if (
        not session_ids
        or any(not sid for sid in session_ids)
        or len(set(session_ids)) != len(session_ids)
    ):
        raise ValueError("Input requires unique, nonempty session IDs")

    stem = Path(args.session_path).stem
    out_dir = corruption_model_dir("main", args.model_path)
    base_path = out_dir / f"{stem}_base_corruptions.json"
    styled_path = out_dir / f"{stem}_styled_corruptions.json"
    grouped_path = out_dir / f"{stem}_grouped_corruptions.json"

    prepare_checkpoint(
        out_dir / f"{stem}_corruption.inputs.json",
        Path(args.session_path),
        {"model": args.model_path, "styles": DEFAULT_STYLE_TYPES},
        [base_path, styled_path, grouped_path],
        args.resume,
    )

    grouped_results: List[Dict[str, Any]] = []
    completed_ids = set()
    if args.resume:
        session_ids = [session.get("session_id") for session in sessions]
        if any(not sid for sid in session_ids) or len(set(session_ids)) != len(
            session_ids
        ):
            raise ValueError("Resume requires unique, nonempty input session IDs")
        if grouped_path.exists():
            grouped_results = load_json(grouped_path)
            if not isinstance(grouped_results, list):
                raise ValueError("Saved grouped results must be a list")
            for grouped in grouped_results:
                sid = grouped.get("session_id")
                if sid not in session_ids or sid in completed_ids:
                    raise ValueError(
                        f"Saved session ID is unknown or duplicated: {sid}"
                    )
                for key in ("base_corruptions", "styled_corruptions"):
                    if not isinstance(grouped.get(key), list):
                        raise ValueError(f"Saved session {sid} has invalid {key}")
                completed_ids.add(sid)
    reused_sessions = len(grouped_results)
    pending = [
        (idx, session)
        for idx, session in enumerate(sessions)
        if session.get("session_id") not in completed_ids
    ]
    print(
        f"Sessions: total={len(sessions)} reused={reused_sessions} pending={len(pending)}"
    )

    with ThreadPoolExecutor(max_workers=args.session_workers) as executor:
        future_to_session = {
            executor.submit(
                process_one_session,
                session,
                args.model_path,
                args.style_workers,
            ): (session_idx, session)
            for session_idx, session in pending
        }

        for fut in tqdm(
            as_completed(future_to_session),
            total=len(pending),
            desc="processing sessions",
        ):
            session_idx, session = future_to_session[fut]

            try:
                session_base_records, session_styled_records, grouped = fut.result()

                grouped_results.append(grouped)

                print(
                    f"[OK] processed session_index={session.get('session_index', session_idx)} "
                    f"session_id={session.get('session_id')} "
                    f"base={len(session_base_records)} styled={len(session_styled_records)}"
                )

            except Exception as e:
                print(
                    f"[ERROR] failed on session_index={session.get('session_index', session_idx)} "
                    f"session_id={session.get('session_id')} "
                    f"subject={session.get('subject')} topic={session.get('topic')} "
                    f"error={repr(e)}"
                )

    # The grouped output is authoritative, including sessions reused on resume.
    all_base_records = [
        record for group in grouped_results for record in group["base_corruptions"]
    ]
    all_styled_records = [
        record for group in grouped_results for record in group["styled_corruptions"]
    ]

    save_json(base_path, all_base_records)
    save_json(styled_path, all_styled_records)
    save_json(grouped_path, grouped_results)

    print(f"Saved flat base corruptions to: {base_path}")
    print(f"Saved flat styled corruptions to: {styled_path}")
    print(f"Saved grouped per-session results to: {grouped_path}")

    successful_sessions = len(grouped_results)
    failed_sessions = len(sessions) - successful_sessions
    print(
        f"Session summary: total={len(sessions)} "
        f"successful={successful_sessions} reused={reused_sessions} "
        f"newly_successful={successful_sessions - reused_sessions} failed={failed_sessions}",
        flush=True,
    )

    if failed_sessions:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
