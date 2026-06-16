import json
import os
import sys
import threading

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

# Load .env from project root regardless of CWD
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=os.path.abspath(_env_path))

# Ensure backend directory is on sys.path for relative imports
sys.path.insert(0, os.path.dirname(__file__))

from database import engine, SessionLocal
from models import Base, Employee
from policy_loader import load_policies
from routers import employees, submissions, policy_qa

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Northwind Expense Review", version="1.0.0")

_allowed_origins = [
    "http://localhost:5173",
    "http://localhost:4173",
]
_extra_origin = os.environ.get("ALLOWED_ORIGIN")
if _extra_origin:
    _allowed_origins.append(_extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(employees.router, prefix="/api")
app.include_router(submissions.router, prefix="/api")
app.include_router(policy_qa.router, prefix="/api")

SUBMISSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "submissions")


@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})


@app.on_event("startup")
def startup():
    # Run seeding and policy loading in a background thread so the server
    # can accept healthcheck requests immediately on startup.
    def _init():
        try:
            _seed_employees()
        except Exception as e:
            print(f"Warning: employee seeding failed: {e}")
        try:
            load_policies()
            print("Policies loaded and cached.")
        except Exception as e:
            print(f"Warning: policy loading failed: {e}")

    threading.Thread(target=_init, daemon=True).start()


def _seed_employees():
    db = SessionLocal()
    try:
        sub_dir = os.path.abspath(SUBMISSIONS_DIR)
        if not os.path.isdir(sub_dir):
            return

        for folder in sorted(os.listdir(sub_dir)):
            json_path = os.path.join(sub_dir, folder, "employee_info.json")
            if not os.path.isfile(json_path):
                continue

            with open(json_path) as f:
                data = json.load(f)

            emp_id = data.get("employee_id")
            if not emp_id:
                continue

            existing = db.query(Employee).filter(Employee.employee_id == emp_id).first()
            if existing:
                continue

            emp = Employee(
                employee_id=emp_id,
                name=data.get("name", ""),
                grade=data.get("grade", 1),
                title=data.get("title"),
                department=data.get("department"),
                manager_id=data.get("manager_id"),
                home_base=data.get("home_base"),
            )
            db.add(emp)

        db.commit()
        print("Employees seeded from data/submissions/.")
    finally:
        db.close()


# Serve the built frontend in production
_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="static")
