from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Student(BaseModel):
    name: str
    id: Optional[str] = None


class DialogueTurn(BaseModel):
    turn: int
    speaker: str
    action: str
    segment: int
    utterance: str


class SessionRecord(BaseModel):
    session_id: str
    subject: str
    topic: str
    lesson_segments: List[str]
    students: List[Student]
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


class LanguagePhenomenonCorruptionRecord(BaseModel):
    session_id: str
    question_turn_index: int
    question_turn_number: int
    phenomenon_type: str
    degree: int = 1
    record_type: str = "language_phenomenon"
    num_added_words: Optional[int] = None
    selected_item: str
    selected_items: List[str] = Field(default_factory=list)
    num_instances: int = 0
    selection_reason: str
    base_wrong_answer: str
    updated_wrong_answer: str
    selected_item_validator_passed: bool
    selected_item_validator_reason: str
    answer_eval: str
    incorrect_validator_passed: bool
    incorrect_validator_reason: str


class DialectPhenomenonCorruptionRecord(BaseModel):
    session_id: str
    question_turn_index: int
    question_turn_number: int
    phenomenon_type: str
    phenomenon_definition: str
    yale_url: str
    record_type: str = "dialect_phenomenon"
    applicable: bool
    applicability_reason: str
    num_added_words: int = 0
    selected_item: str = ""
    selected_items: List[str] = Field(default_factory=list)
    num_instances: int = 0
    selection_reason: str
    base_wrong_answer: str
    updated_wrong_answer: str
    selected_item_validator_passed: bool
    selected_item_validator_reason: str
    answer_eval: str
    incorrect_validator_passed: bool
    incorrect_validator_reason: str


class DialectSpeakerCorruptionRecord(BaseModel):
    session_id: str
    question_turn_index: int
    question_turn_number: int
    dialect_type: str
    phenomenon_type: str
    record_type: str = "dialect_speaker"
    applicable: bool
    applicability_reason: str
    applied_features: List[str] = Field(default_factory=list)
    feature_evidence: List[Dict[str, str]] = Field(default_factory=list)
    num_added_words: int = 0
    selected_item: str = ""
    selected_items: List[str] = Field(default_factory=list)
    num_instances: int = 0
    selection_reason: str
    base_wrong_answer: str
    updated_wrong_answer: str
    selected_item_validator_passed: bool
    selected_item_validator_reason: str
    answer_eval: str
    incorrect_validator_passed: bool
    incorrect_validator_reason: str


class VigilanceEvalRecord(BaseModel):
    evaluation_status: str = "valid"
    evaluation_error: Optional[str] = None
    raw_evaluator_response: Any = None
    session_id: str
    subject: str
    topic: str
    question_turn_index: int
    question_turn_number: int
    style_type: str
    asked_question: str
    answering_student: Optional[str] = None
    counterfactual_wrong_answer: str
    teacher_action_generated: str
    teacher_followup: str
    answer_eval: str
    answer_eval_justification: str
    teacher_epistemic_vigilance: str
    teacher_action_evaluated: str
    justification: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LanguagePhenomenonVigilanceEvalRecord(BaseModel):
    evaluation_status: str = "valid"
    evaluation_error: Optional[str] = None
    raw_evaluator_response: Any = None
    session_id: str
    subject: str
    topic: str
    question_turn_index: int
    question_turn_number: int
    phenomenon_type: str
    selected_item: str
    selected_items: List[str] = Field(default_factory=list)
    num_instances: int = 0
    selection_reason: str
    asked_question: str
    answering_student: Optional[str] = None
    counterfactual_wrong_answer: str
    teacher_action_generated: str
    teacher_followup: str
    answer_eval: str
    answer_eval_justification: str
    teacher_epistemic_vigilance: str
    teacher_action_evaluated: str
    justification: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
