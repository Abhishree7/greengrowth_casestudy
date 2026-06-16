from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Employee
from schemas import EmployeeCreate, EmployeeOut

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    return db.query(Employee).order_by(Employee.name).all()


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: str, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


@router.post("", response_model=EmployeeOut, status_code=201)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    existing = db.query(Employee).filter(Employee.employee_id == payload.employee_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Employee ID already exists")
    emp = Employee(**payload.model_dump())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp
