import argparse
from pathlib import Path
from typing import Any, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from config import REPLAY_DIR
from profiles import PROFILES
from store_utils import load_json, save_json
from replay.replay import replay_session_with_new_roster


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_path", type=str, required=True)
    parser.add_argument("--target_profile_type", type=str, required=True)
    parser.add_argument("--model_path", type=str, required=True)
    parser.add_argument("--num_raisers", type=int, default=2)
    parser.add_argument("--num_workers", type=int, default=2)
    parser.add_argument("--target_group", type=str, default=None)
    return parser.parse_args()


def normalize_sessions(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    return [data]


def process_one_session(session: Dict, target_profile_type: str, model_path: str, num_raisers: int, target_group: str = None) -> Dict:
    new_students = PROFILES[target_profile_type]
    replayed = replay_session_with_new_roster(
        session_dict=session,
        new_students=new_students,
        target_profile_type=target_profile_type,
        target_group=target_group,
        model_path=model_path,
        num_raisers=num_raisers,
    )
    return replayed

def main():
    args = parse_args()
    data = load_json(Path(args.session_path))
    sessions = normalize_sessions(data)

    replayed_sessions = []

    with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        futures = [
            executor.submit(
                process_one_session,
                session,
                args.target_profile_type,
                args.model_path,
                args.num_raisers,
                args.target_group,
            )
            for session in sessions
        ]

        for fut in tqdm(as_completed(futures), total=len(futures), desc="replaying sessions"):
            replayed_sessions.append(fut.result())

    stem = Path(args.session_path).stem
    out_path = REPLAY_DIR / f"{stem}_replayed_{args.target_profile_type}_{args.target_group}.json"
    save_json(out_path, replayed_sessions)
    print(f"Saved replayed sessions to: {out_path}")


if __name__ == "__main__":
    main()