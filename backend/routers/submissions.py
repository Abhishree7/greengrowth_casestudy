import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import Employee, Submission, LineItem, Override
from schemas import SubmissionCreate, SubmissionOut, SubmissionSummary, OverrideCreate, OverrideOut
from receipt_extractor import extract_receipt
from review_engine import review_line_item

router = APIRouter(prefix="/submissions", tags=["submissions"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")


@router.post("", response_model=SubmissionOut, status_code=201)
def create_submission(payload: SubmissionCreate, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.employee_id == payload.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    sub = Submission(
        employee_id=payload.employee_id,
        trip_purpose=payload.trip_purpose,
        trip_dates=payload.trip_dates,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    # Eager-load for response
    return db.query(Submission).options(
        joinedload(Submission.employee),
        joinedload(Submission.line_items).joinedload(LineItem.override),
    ).filter(Submission.id == sub.id).first()


@router.get("", response_model=list[SubmissionSummary])
def list_submissions(
    employee_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Submission).options(
        joinedload(Submission.employee),
        joinedload(Submission.line_items),
    )
    if employee_id:
        q = q.filter(Submission.employee_id == employee_id)
    if status:
        q = q.filter(Submission.status == status)

    submissions = q.order_by(Submission.created_at.desc()).all()

    results = []
    for sub in submissions:
        flagged = sum(
            1 for li in sub.line_items
            if li.verdict in ("flagged", "rejected")
        )
        results.append(
            SubmissionSummary(
                **{
                    "id": sub.id,
                    "employee_id": sub.employee_id,
                    "trip_purpose": sub.trip_purpose,
                    "trip_dates": sub.trip_dates,
                    "status": sub.status,
                    "total_amount": sub.total_amount,
                    "reimbursable_amount": sub.reimbursable_amount,
                    "created_at": sub.created_at,
                    "employee": sub.employee,
                    "line_item_count": len(sub.line_items),
                    "flagged_count": flagged,
                }
            )
        )
    return results


@router.get("/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: int, db: Session = Depends(get_db)):
    sub = (
        db.query(Submission)
        .options(
            joinedload(Submission.employee),
            joinedload(Submission.line_items).joinedload(LineItem.override),
        )
        .filter(Submission.id == submission_id)
        .first()
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


@router.post("/{submission_id}/receipts", response_model=SubmissionOut)
def upload_receipts(
    submission_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if sub.status == "reviewing":
        raise HTTPException(status_code=409, detail="Review already in progress")

    upload_dir = os.path.join(os.path.abspath(UPLOAD_DIR), str(submission_id))
    os.makedirs(upload_dir, exist_ok=True)

    for upload in files:
        safe_name = os.path.basename(upload.filename or "receipt")
        dest = os.path.join(upload_dir, safe_name)
        with open(dest, "wb") as f:
            shutil.copyfileobj(upload.file, f)

        line_item = LineItem(
            submission_id=submission_id,
            receipt_filename=safe_name,
            receipt_path=dest,
        )
        db.add(line_item)

    db.commit()

    return db.query(Submission).options(
        joinedload(Submission.employee),
        joinedload(Submission.line_items).joinedload(LineItem.override),
    ).filter(Submission.id == submission_id).first()


@router.post("/{submission_id}/review", response_model=SubmissionOut)
def review_submission(submission_id: int, db: Session = Depends(get_db)):
    sub = (
        db.query(Submission)
        .options(
            joinedload(Submission.employee),
            joinedload(Submission.line_items),
        )
        .filter(Submission.id == submission_id)
        .first()
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    pending = [li for li in sub.line_items if li.verdict is None]
    if not pending:
        raise HTTPException(status_code=409, detail="All line items already reviewed")

    sub.status = "reviewing"
    db.commit()

    employee_dict = {
        "name": sub.employee.name,
        "grade": sub.employee.grade,
        "title": sub.employee.title,
        "department": sub.employee.department,
        "home_base": sub.employee.home_base,
    }

    try:
        for li in pending:
            extracted = extract_receipt(li.receipt_path)
            li.extracted_data = extracted
            li.merchant = extracted.get("merchant")
            li.category = extracted.get("category")
            li.amount = extracted.get("total_amount")
            li.date = extracted.get("date")

            verdict = review_line_item(
                extracted=extracted,
                employee=employee_dict,
                trip_purpose=sub.trip_purpose or "",
                trip_dates=sub.trip_dates or "",
            )
            li.verdict = verdict["verdict"]
            li.confidence = verdict["confidence"]
            li.reasoning = verdict["reasoning"]
            li.policy_citations = verdict["policy_citations"]
            li.reimbursable_amount = verdict["reimbursable_amount"]
            li.flags = verdict.get("flags", [])
            db.add(li)

        total = sum(li.amount or 0 for li in sub.line_items)
        reimbursable = sum(li.reimbursable_amount or 0 for li in sub.line_items)
        sub.total_amount = total
        sub.reimbursable_amount = reimbursable
        sub.status = "reviewed"
        db.commit()

    except Exception as e:
        sub.status = "draft"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Review failed: {e}")

    return db.query(Submission).options(
        joinedload(Submission.employee),
        joinedload(Submission.line_items).joinedload(LineItem.override),
    ).filter(Submission.id == submission_id).first()


@router.patch("/line-items/{line_item_id}/override", response_model=OverrideOut, status_code=201)
def override_verdict(
    line_item_id: int,
    payload: OverrideCreate,
    db: Session = Depends(get_db),
):
    li = db.query(LineItem).filter(LineItem.id == line_item_id).first()
    if not li:
        raise HTTPException(status_code=404, detail="Line item not found")
    if not li.verdict:
        raise HTTPException(status_code=409, detail="Line item has not been reviewed yet")

    allowed_verdicts = {"compliant", "flagged", "rejected", "needs_info"}
    if payload.new_verdict not in allowed_verdicts:
        raise HTTPException(status_code=422, detail=f"verdict must be one of {allowed_verdicts}")

    if li.override:
        li.override.original_verdict = li.override.original_verdict  # keep first original
        li.override.new_verdict = payload.new_verdict
        li.override.reviewer_comment = payload.reviewer_comment
        li.override.reviewer = payload.reviewer
        db.commit()
        db.refresh(li.override)
        return li.override

    override = Override(
        line_item_id=line_item_id,
        original_verdict=li.verdict,
        new_verdict=payload.new_verdict,
        reviewer_comment=payload.reviewer_comment,
        reviewer=payload.reviewer,
    )
    db.add(override)
    db.commit()
    db.refresh(override)
    return override
