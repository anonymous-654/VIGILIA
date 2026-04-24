import json
from typing import Any, Dict, Iterable, List, Tuple, Union
from tqdm import tqdm
import argparse
from enums import EvalType
from profiles import PROFILES
from session import run_class_session
from subjects import COURSE_SUBJECTS
from vigilance.session import run_class_session_for_vigilance


profiles = PROFILES

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max_turns', type=int, required=False)
    parser.add_argument('--num_runs', type=int, required=True)
    parser.add_argument('--profile_type', type=str, required=True)
    parser.add_argument('--model_path', type=str, required=True)
    parser.add_argument('--eval_type', type=str, required=True)
    parser.add_argument('--attack_type', type=str, required=False)
    
    return parser.parse_args()

def main(args):

    results: List[Dict[str, Any]] = []
    
    max_turns = args.max_turns
    num_runs = args.num_runs
    profile_type = args.profile_type
    model_path = args.model_path
    eval_type = args.eval_type
    attack_type = args.attack_type
    safe_model_path = model_path.replace("/", "_").replace(" ", "_")

    prompt_tokens = 0
    completion_tokens = 0
    bad_turns = 0

    questions_asked = []
    wrong_answers = []
    num_wrong_answers = 0
    vigilance_list = []

    if "meta" in model_path:
        out_path: str = f"sessions_summary_Llama-3.3-70B_{profile_type}_{eval_type}_{attack_type}_{num_runs}_{max_turns}.json"
    else:
        out_path: str = f"sessions_summary_{safe_model_path}_{profile_type}_{eval_type}_{attack_type}_{num_runs}_{max_turns}.json"


    students = profiles[profile_type]
    SESSION_PAIRS = [(subj, topic) for subj, topics in COURSE_SUBJECTS.items() for topic in topics]
    TOTAL_SESSIONS = len(SESSION_PAIRS)
    
    for session_idx in tqdm(range(num_runs), desc=f"Sessions[{profile_type}]", leave=False):
        # conversation_history, selected_speakers, num_questions = run_class_section(students, model_path, max_turns)
        if eval_type == EvalType.VIGILANCE:
            subject, topic = SESSION_PAIRS[session_idx % TOTAL_SESSIONS]
            try:
                (conversation_history, selected_speakers, selected_speaker_indices, 
                all_hand_raises, num_questions, questions_asked, wrong_answers, 
                num_wrong_answers,  vigilance_list, turns_ran, tpt, tct) = run_class_session_for_vigilance(
                    students, model_path, subject, topic, profile_type, attack_type)
            except Exception as e:
                print(f"Some error actually occured for {subject} and topic {topic}, \n error is {e}")
                continue
        else:
            subject, topic = SESSION_PAIRS[0]
            (conversation_history, selected_speakers, 
             selected_speaker_indices, 
             all_hand_raises, num_questions, turns_ran, tpt, tct)= run_class_session(students, model_path, subject, topic, profile_type)

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
            "wrong_answers": wrong_answers,
            "num_wrong_answers": num_wrong_answers,
            "vigilance_list": vigilance_list
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