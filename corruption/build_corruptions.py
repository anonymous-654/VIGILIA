import argparse
from pathlib import Path
from typing import Any, Dict, List

from tqdm import tqdm

from config import CORRUPTION_DIR, DEFAULT_STYLE_TYPES
from corruption.base_corruptor import generate_base_corruption
from corruption.claims import extract_claims
from corruption.gold import extract_question_gold_records
from corruption.selector import choose_claim_and_error_type
from corruption.style_corruptor import apply_style_corruption
from store_utils import load_json, save_json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_path", type=str, required=True)
    parser.add_argument("--model_path", type=str, required=True)
    return parser.parse_args()


def normalize_sessions(data: Any) -> List[Dict[str, Any]]:
    """
    Accept either:
    - one session dict
    - a list of session dicts
    and always return a list.
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError(f"Unsupported session file format: {type(data)}")


def process_one_session(session: Dict[str, Any], model_path: str):
    """
    Build base and styled corruptions for one session.
    Returns:
        session_base_records, session_styled_records
    """
    gold_records = extract_question_gold_records(session)

    session_base_records = []
    session_styled_records = []

    for record in tqdm(gold_records, total=len(gold_records), desc='claim  extraction'):
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
        session_base_records.append(base.model_dump())

        for style in tqdm(DEFAULT_STYLE_TYPES, total=len(DEFAULT_STYLE_TYPES), desc='processing sytles'):
            styled = apply_style_corruption(
                model_path=model_path,
                session_id=record.session_id,
                question_turn_index=record.question_turn_index,
                question_turn_number=record.question_turn_number,
                question_text=record.question_text,
                base_wrong_answer=base.base_wrong_answer,
                style_type=style,
            )
            session_styled_records.append(styled.model_dump())

    return session_base_records, session_styled_records


def main():
    args = parse_args()
    data = load_json(Path(args.session_path))
    sessions = normalize_sessions(data)

    all_base_records = []
    all_styled_records = []
    grouped_results = []
    for session_idx, session in tqdm(enumerate(sessions), total=len(session), desc='processing sessions'):
        try:
            session_base_records, session_styled_records = process_one_session(
                session=session,
                model_path=args.model_path,
            )

            all_base_records.extend(session_base_records)
            all_styled_records.extend(session_styled_records)

            grouped_results.append(
                {
                    "session_id": session.get("session_id"),
                    "session_index": session.get("session_index", session_idx),
                    "subject": session.get("subject"),
                    "topic": session.get("topic"),
                    "num_base_corruptions": len(session_base_records),
                    "num_styled_corruptions": len(session_styled_records),
                    "base_corruptions": session_base_records,
                    "styled_corruptions": session_styled_records,
                }
            )

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
                f"error={e}"
            )

    stem = Path(args.session_path).stem

    save_json(CORRUPTION_DIR / f"{stem}_base_corruptions.json", all_base_records)
    save_json(CORRUPTION_DIR / f"{stem}_styled_corruptions.json", all_styled_records)
    save_json(CORRUPTION_DIR / f"{stem}_grouped_corruptions.json", grouped_results)

    print(f"Saved flat base corruptions to: {CORRUPTION_DIR / f'{stem}_base_corruptions.json'}")
    print(f"Saved flat styled corruptions to: {CORRUPTION_DIR / f'{stem}_styled_corruptions.json'}")
    print(f"Saved grouped per-session results to: {CORRUPTION_DIR / f'{stem}_grouped_corruptions.json'}")


if __name__ == "__main__":
    main()