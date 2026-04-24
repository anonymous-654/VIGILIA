from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class StudentProfile(BaseModel):
    name: str
    gender: Optional[str] = None
    grade_level: Optional[str] = None
    gpa_band: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class DialogueTurn(BaseModel):
    turn: int
    speaker: str
    action: str
    segment: int
    utterance: str

class SessionRecord(BaseModel):
    session_id: str
    profile_type: str
    subject: str
    topic: str
    lesson_segments: List[str]
    students: List[StudentProfile]
    conversation_history: List[DialogueTurn]
    selected_speakers: List[str]
    selected_speaker_indices: List[Optional[int]]
    all_hand_raises: List[List[str]]
    num_questions: int
    questions_asked: List[str]
    turns_ran: int
    prompt_tokens: int
    completion_tokens: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClaimUnit(BaseModel):
    claim_id: str
    claim_text: str
    claim_role: Optional[str] = None


class GoldAnswerRecord(BaseModel):
    session_id: str
    question_turn_index: int
    question_turn_number: int
    question_text: str
    original_student: Optional[str] = None
    original_student_answer: Optional[str] = None
    gold_answer: str
    claims: List[ClaimUnit]

class BaseCorruptionRecord(BaseModel):
    session_id: str
    question_turn_index: int
    question_turn_number: int
    question_text: str
    gold_answer: str
    selected_claim_id: str
    selected_claim_text: str
    selected_error_type: str
    error_selection_reason: str
    corrupted_claim_text: str
    base_wrong_answer: str
    validator_verdict: str
    validator_reasoning: str


class StyledCorruptionRecord(BaseModel):
    session_id: str
    question_turn_index: int
    question_turn_number: int
    style_type: str
    base_wrong_answer: str
    styled_wrong_answer: str
    style_validator_passed: bool
    style_validator_reason: str
    answer_eval: str
    incorrect_validator_passed: bool
    incorrect_validator_reason: str

class VigilanceEvalRecord(BaseModel):
    session_id: str
    question_turn_index: int
    question_turn_number: int
    style_type: str
    asked_question: str
    counterfactual_wrong_answer: str
    teacher_action_generated: str
    teacher_followup: str
    answer_eval: str
    answer_eval_justification: str
    teacher_epistemic_vigilance: str
    teacher_action_evaluated: str
    justification: str
    metadata: Dict[str, Any] = Field(default_factory=dict)