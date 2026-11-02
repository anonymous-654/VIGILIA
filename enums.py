from enum import Enum


class AttackType(str, Enum):
    CREDIBILITY = "credibility"
    ANECDOTE = "anecdote"
    EMOTION = "emotion"
    PLAIN = "plain"
