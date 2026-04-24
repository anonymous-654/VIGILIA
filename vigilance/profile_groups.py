from typing import Dict, List


PROFILE_GROUPS = {
    "plain": {
        "western": ["Alex", "William", "Chloe", "Lucas", "Olivia"],
        "non_western": ["Zawadi", "Amina", "Chinazaekpere", "Ugonna", "Kwame"],
    },
    "gender": {
        "female_coded": ["Amelia", "Charlotte", "Olivia", "Chloe", "Madison"],
        "male_coded": ["William", "Lucas", "Benjamin", "Noah", "Andrew"],
    },
    "ex_gender": {
        "F": ["Amelia", "Charlotte", "Olivia", "Chloe", "Madison"],
        "M": ["William", "Lucas", "Benjamin", "Noah", "Andrew"],
    },
}


def get_students_in_group(students: List[Dict], profile_type: str, group_name: str) -> List[Dict]:
    allowed_names = set(PROFILE_GROUPS[profile_type][group_name])
    return [s for s in students if s["name"] in allowed_names]


def infer_group_for_student(student: Dict, profile_type: str) -> str:
    name = student["name"]
    for group, names in PROFILE_GROUPS[profile_type].items():
        if name in names:
            return group
    return "unknown"

def aggregate_all_names() -> List[str]:
    names = set()
    for profile_type, groups in PROFILE_GROUPS.items():
        for group_names in groups.values():
            names.update(group_names)
    return list(names)