from enum import Enum

class EvalType(str, Enum):
    VIGILANCE = "vigilance"
    FAIRNESS = "fairness"
   
class AttackType(str, Enum):
    CREDIBILITY = "credibility"
    ANECDOTE = "anecdote"
    EMOTION = "emotion"
    PLAIN = "plain"
