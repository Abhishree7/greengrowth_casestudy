from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EmployeeCreate(BaseModel):
    employee_id: str
    name: str
    grade: int
    title: Optional[str] = None
    department: Optional[str] = None
    manager_id: Optional[str] = None
    home_base: Optional[str] = None


class EmployeeOut(BaseModel):
    id: int
    employee_id: str
    name: str
    grade: int
    title: Optional[str]
    department: Optional[str]
    manager_id: Optional[str]
    home_base: Optional[str]

    model_config = {"from_attributes": True}


class SubmissionCreate(BaseModel):
    employee_id: str
    trip_purpose: str
    trip_dates: str


class PolicyCitation(BaseModel):
    doc_id: str
    section: str
    quoted_text: str


class OverrideOut(BaseModel):
    id: int
    original_verdict: str
    new_verdict: str
    reviewer_comment: str
    reviewer: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LineItemOut(BaseModel):
    id: int
    receipt_filename: str
    category: Optional[str]
    merchant: Optional[str]
    amount: Optional[float]
    date: Optional[str]
    verdict: Optional[str]
    confidence: Optional[float]
    reasoning: Optional[str]
    policy_citations: Optional[list]
    reimbursable_amount: Optional[float]
    flags: Optional[list]
    extracted_data: Optional[dict]
    override: Optional[OverrideOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class SubmissionOut(BaseModel):
    id: int
    employee_id: str
    trip_purpose: Optional[str]
    trip_dates: Optional[str]
    status: str
    total_amount: float
    reimbursable_amount: float
    created_at: datetime
    employee: EmployeeOut
    line_items: list[LineItemOut] = []

    model_config = {"from_attributes": True}


class SubmissionSummary(BaseModel):
    id: int
    employee_id: str
    trip_purpose: Optional[str]
    trip_dates: Optional[str]
    status: str
    total_amount: float
    reimbursable_amount: float
    created_at: datetime
    employee: EmployeeOut
    line_item_count: int = 0
    flagged_count: int = 0

    model_config = {"from_attributes": True}


class OverrideCreate(BaseModel):
    new_verdict: str
    reviewer_comment: str
    reviewer: str = "Finance Reviewer"


class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class PolicyQuestion(BaseModel):
    question: str
    history: list[ChatMessage] = []   # prior turns in the conversation


class PolicyAnswer(BaseModel):
    answer: str
    citations: list[PolicyCitation]
    is_in_scope: bool
