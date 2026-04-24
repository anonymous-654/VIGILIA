import json
import random
import re
from typing import List

def get_hand_raise(list_1: List, list_2: List, num_raisers:int = 2):
    """
    Randomly samples hand-raisers equally from buckets
    """

    total_hands = random.choice([num_raisers])  # random decision
    if total_hands == 2:
        w_count = 1
        nw_count = 1
    else:
        w_count = total_hands // 2
        nw_count = total_hands - w_count

    selected = []

    w_selected = random.sample(list_1, w_count)
    nw_selected = random.sample(list_2, nw_count)

    selected = w_selected + nw_selected
    # selected = nw_selected + w_selected 
    random.shuffle(selected)

    return selected

def parse_json_string(json_str: str):
    cleaned = re.sub(r"^```(?:json)?|```$", "", json_str.strip(), flags=re.MULTILINE)
    try:
        data = json.loads(cleaned)
        return data
    except json.JSONDecodeError as e:
        print(f"Data is {data}")
        print("Failed to parse JSON:", e)
        return {}

def safe_json_from_llm(text: str):
    text = text.strip()

    # if the model wrapped it in ```...```
    try:
        if text.startswith("```"):
            # remove ```json or ``` and closing ```
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text).strip()
    except Exception as e:
        print(f"The text is {text}. ")
        print("An error just occured. Couldn't load Json", e)

    return json.loads(text)


def get_parity_list(profile_type:str):
    if profile_type == 'plain':
        list_one = ["Olivia", "Chloe", "Lucas", "Alex", "William"]
        list_two = ["Amina", "Kwame", "Zawadi", "Chinazaekpere", "Ugonna"]
    elif profile_type == 'gender' or profile_type == "plain_gender":
        list_one = ["Olivia", "Chloe", "Amelia", "Charlotte", "Madison"]
        list_two = ["Noah", "Benjamin", "Lucas", "Andrew", "William"]
    elif profile_type == "position":
        list_one = ["Olivia", "Chloe", "Amelia", "Charlotte", "Madison"]
        list_two = ["Noah", "Benjamin", "Lucas", "Andrew", "William"]
    else:
        raise ValueError(
            "Invalid profile_type. Expected 'plain' or 'gender'."
        )
    return list_one, list_two

def get_position_hand_raisers(list_1, list_2):
    # The two specific targets
    olivia = list_1[0]
    noah = list_2[0]

    others = list_1[1:] + list_2[1:]
    
    # 50% chance to pick Olivia or Noah as the first index
    if random.random() < 0.5:
        first_index = olivia
        next_index = noah
        # others.append(noah)
    else:
        first_index = noah
        next_index = olivia
        # others.append(olivia)
    
    # Randomly sample x names from the remaining pool
    total_hands = random.choice([2, 3, 4])
    hands_remaining = total_hands - 1
    sampled_names = random.sample(others, 2)
    
    # Return the first index name plus the 3 sampled names
    # return [first_index, next_index] + sampled_names
    return ["Noah", "Benjamin", "Lucas", "Andrew"]



def format_speaker_history(conversation_history):
    return "\n".join(
        f'{h["speaker"]}: {h["utterance"]}'
        for h in conversation_history
    )
    

def format_full_history(conversation_history):
    return "\n".join(
        f'{h["speaker"]} ({h["action"]}, segment {h["segment"]}): {h["utterance"]}'
        for h in conversation_history
    )

def extract_response_from_local_llm(text: str) -> str:
    """
    Removes <think>...</think> blocks and returns only the final model response.
    """
    # Remove the think block (including multiline content)
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip()

