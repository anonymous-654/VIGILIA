"""Baseline failure rates by original within-session question position."""

from collections import defaultdict
from metrics.common import key
from metrics.vfr import compute_vfr


def position_bins(records):
    sessions = defaultdict(set)
    for row in records:
        session, question = key(row)
        sessions[session].add(question)
    bins = {}
    for session, questions in sessions.items():
        ordered = sorted(questions, key=lambda q: float(q))
        for split, labels in [
            ("halves", ["first_half", "second_half"]),
            ("thirds", ["first_third", "second_third", "third_third"]),
        ]:
            size, remainder = divmod(len(ordered), len(labels))
            offset = 0
            for i, label in enumerate(labels):
                count = size + (i < remainder)
                for question in ordered[offset : offset + count]:
                    bins.setdefault((session, question), {})[split] = label
                offset += count
    return bins


def compute_positions(records, column, baseline):
    # Rank all observed questions before filtering validity, verdict, or condition.
    bins = position_bins(records)
    base = [row for row in records if row[column] == baseline]
    results = []
    for split, labels in [
        ("halves", ["first_half", "second_half"]),
        ("thirds", ["first_third", "second_third", "third_third"]),
    ]:
        for label in labels:
            selected = [row for row in base if bins[key(row)][split] == label]
            results.append(
                dict(
                    condition=baseline,
                    split=split,
                    position=label,
                    **compute_vfr(selected),
                )
            )
    return results
