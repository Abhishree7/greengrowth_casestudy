from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    grade = Column(Integer, nullable=False)
    title = Column(String)
    department = Column(String)
    manager_id = Column(String)
    home_base = Column(String)

    submissions = relationship("Submission", back_populates="employee")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)
    trip_purpose = Column(String)
    trip_dates = Column(String)
    status = Column(String, default="draft")  # draft | reviewing | reviewed
    total_amount = Column(Float, default=0.0)
    reimbursable_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="submissions")
    line_items = relationship("LineItem", back_populates="submission", cascade="all, delete-orphan")


class LineItem(Base):
    __tablename__ = "line_items"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    receipt_filename = Column(String, nullable=False)
    receipt_path = Column(String, nullable=False)
    category = Column(String)           # meal | lodging | transport | conference | other
    merchant = Column(String)
    amount = Column(Float)
    date = Column(String)
    extracted_data = Column(JSON)       # full extraction result
    verdict = Column(String)            # compliant | flagged | rejected | needs_info
    confidence = Column(Float)
    reasoning = Column(Text)
    policy_citations = Column(JSON)     # [{doc_id, section, quoted_text}]
    reimbursable_amount = Column(Float)
    flags = Column(JSON)                # [string]
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("Submission", back_populates="line_items")
    override = relationship("Override", back_populates="line_item", uselist=False)


class Override(Base):
    __tablename__ = "overrides"

    id = Column(Integer, primary_key=True, index=True)
    line_item_id = Column(Integer, ForeignKey("line_items.id"), nullable=False)
    original_verdict = Column(String, nullable=False)
    new_verdict = Column(String, nullable=False)
    reviewer_comment = Column(Text, nullable=False)
    reviewer = Column(String, default="Finance Reviewer")
    created_at = Column(DateTime, default=datetime.utcnow)

    line_item = relationship("LineItem", back_populates="override")
