import json
from typing import Any, Dict, Iterable, List, Tuple, Union
from tqdm import tqdm
import argparse
from enums import EvalType
from classroom.session import run_class_session
from profiles import PROFILES
from subjects import COURSE_SUBJECTS


profiles = PROFILES

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max_turns', type=int, required=False)
    parser.add_argument('--num_runs', type=int, required=True)
    parser.add_argument('--profile_type', type=str, required=True)
    parser.add_argument('--model_path', type=str, required=True)
    parser.add_argument('--eval_type', type=str, required=True)
    parser.add_argument('--num_raisers', type=int, required=False)
    
    return parser.parse_args()

def main(args):

    results: List[Dict[str, Any]] = []
    
    max_turns = args.max_turns
    num_runs = args.num_runs
    profile_type = args.profile_type
    model_path = args.model_path
    eval_type = args.eval_type
    num_raisers = args.num_raisers

    prompt_tokens = 0
    completion_tokens = 0
    bad_turns = 0

    questions_asked = []

    # Clean the model path to avoid creating unwanted subdirectories
    safe_model_name = model_path.replace("/", "_")
    out_path = f"sessions_summary_{safe_model_name}_{profile_type}_{eval_type}_{num_raisers}_{num_runs}_{max_turns}.json"


    students = profiles[profile_type]
    SESSION_PAIRS = [(subj, topic) for subj, topics in COURSE_SUBJECTS.items() for topic in topics]
    TOTAL_SESSIONS = len(SESSION_PAIRS)
    
    for session_idx in tqdm(range(num_runs), desc=f"Sessions[{profile_type}]", leave=False):
        subject, topic = SESSION_PAIRS[session_idx % TOTAL_SESSIONS]
        try:
            (conversation_history, selected_speakers, selected_speaker_indices, 
            all_hand_raises, num_questions, questions_asked, turns_ran, tpt, tct) = run_class_session(
                students, model_path, subject, topic, profile_type, num_raisers)
        except Exception as e:
            print(f"Some error actually occured for {subject} and topic {topic}, \n error is {e}")
            continue

        prompt_tokens += tpt
        completion_tokens += tct

        if turns_ran >= max_turns: # bad session. ignore all from it 
            print("========This is a bad session=========")
            print(f'Bad Conversation History: {conversation_history}')
            bad_turns += 1
            continue

        results.append({
            "profile_type": profile_type,
            "session_index": session_idx,
            "conversation_history": conversation_history,
            "speakers": selected_speakers,
            "speakers_indexes": selected_speaker_indices,
            "all_hand_raises": all_hand_raises,
            "num_questions": int(num_questions),
            "questions_asked": questions_asked, 
        })
    # print(results[0]["conversation_history"])

    # save results
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


    print(f"====Total Prompt Tokens == {prompt_tokens} =====")
    print(f"====Total Completion Tokens == {completion_tokens} =====")
    print(f"====Total Number of bad turns == {bad_turns} =====")


    return results



if __name__ == "__main__":
    args = parse_args()
    main(args)