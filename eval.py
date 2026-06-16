"""
Evaluation harness for the Northwind Expense Review system.

Usage:
    python eval.py --expected expected.json --base-url http://localhost:8000

Expected JSON schema:
{
  "submissions": [
    {
      "submission_folder": "01_clean_denver",   # folder name under data/submissions/
      "employee_id": "NW-04821",
      "trip_purpose": "...",
      "trip_dates": "...",
      "expected_verdicts": {
        "01_united_airlines.pdf": "compliant",
        "02_marriott_denver.pdf": "compliant",
        ...
      }
    }
  ],
  "qa_tests": [
    {
      "question": "What is the dinner cap for solo travel?",
      "expected_in_scope": true,
      "expected_answer_contains": ["75", "$75"]
    },
    {
      "question": "What is the company's 401k matching policy?",
      "expected_in_scope": false
    }
  ]
}
"""

import argparse
import json
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent
SUBMISSIONS_DIR = BASE_DIR / "data" / "submissions"


def create_submission(base_url: str, emp_id: str, purpose: str, dates: str) -> int:
    r = requests.post(
        f"{base_url}/api/submissions",
        json={"employee_id": emp_id, "trip_purpose": purpose, "trip_dates": dates},
    )
    r.raise_for_status()
    return r.json()["id"]


def upload_receipts(base_url: str, sub_id: int, receipt_dir: Path) -> None:
    files_list = sorted(receipt_dir.glob("*"))
    files = [
        ("files", (f.name, open(f, "rb"), _mime(f)))
        for f in files_list
        if f.is_file()
    ]
    r = requests.post(f"{base_url}/api/submissions/{sub_id}/receipts", files=files)
    for _, (_, fh, _) in files:
        fh.close()
    r.raise_for_status()


def trigger_review(base_url: str, sub_id: int) -> dict:
    print(f"  Running AI review for submission {sub_id}...")
    r = requests.post(f"{base_url}/api/submissions/{sub_id}/review", timeout=300)
    r.raise_for_status()
    return r.json()


def _mime(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".txt": "text/plain",
    }.get(ext, "application/octet-stream")


def eval_submissions(base_url: str, test_cases: list[dict]) -> dict:
    total, correct, cited, low_confidence_wrong = 0, 0, 0, 0

    per_submission = []

    for case in test_cases:
        folder = case["submission_folder"]
        sub_dir = SUBMISSIONS_DIR / folder

        # Load employee info
        emp_json = sub_dir / "employee_info.json"
        with open(emp_json) as f:
            emp = json.load(f)

        emp_id = case.get("employee_id", emp["employee_id"])
        purpose = case.get("trip_purpose", emp.get("trip_purpose", "Business trip"))
        dates = case.get("trip_dates", emp.get("trip_dates", ""))

        print(f"\n[{folder}] employee={emp_id}")

        # Ensure employee exists
        requests.post(
            f"{base_url}/api/employees",
            json={
                "employee_id": emp["employee_id"],
                "name": emp["name"],
                "grade": emp["grade"],
                "title": emp.get("title"),
                "department": emp.get("department"),
                "manager_id": emp.get("manager_id"),
                "home_base": emp.get("home_base"),
            },
        )  # 409 is fine if already exists

        sub_id = create_submission(base_url, emp_id, purpose, dates)
        print(f"  Submission created: id={sub_id}")

        receipt_dir = sub_dir / "receipts"
        upload_receipts(base_url, sub_id, receipt_dir)
        print(f"  Receipts uploaded: {len(list(receipt_dir.glob('*')))} files")

        result = trigger_review(base_url, sub_id)
        line_items = result["line_items"]

        expected: dict[str, str] = case.get("expected_verdicts", {})
        sub_correct, sub_total = 0, 0

        for item in line_items:
            fname = item["receipt_filename"]
            predicted = item.get("override", {}) and item["override"]["new_verdict"] or item["verdict"]
            confidence = item.get("confidence", 1.0) or 1.0
            has_citation = bool(item.get("policy_citations"))

            if fname in expected:
                sub_total += 1
                total += 1
                if has_citation:
                    cited += 1
                if predicted == expected[fname]:
                    sub_correct += 1
                    correct += 1
                else:
                    status = "WRONG"
                    if confidence < 0.7:
                        low_confidence_wrong += 1
                        status += " (low-conf)"
                    print(
                        f"    {fname}: expected={expected[fname]} got={predicted} "
                        f"conf={confidence:.0%} {status}"
                    )
            else:
                print(f"    {fname}: predicted={predicted} conf={confidence:.0%} (no expected)")

        pct = sub_correct / sub_total * 100 if sub_total else 0
        print(f"  Result: {sub_correct}/{sub_total} correct ({pct:.0f}%)")
        per_submission.append(
            {"folder": folder, "correct": sub_correct, "total": sub_total}
        )

    return {
        "verdict_accuracy": correct / total if total else 0,
        "citation_rate": cited / total if total else 0,
        "low_confidence_wrong_rate": low_confidence_wrong / max(total - correct, 1),
        "per_submission": per_submission,
    }


def eval_qa(base_url: str, qa_tests: list[dict]) -> dict:
    correct_scope, total = 0, 0

    for test in qa_tests:
        q = test["question"]
        expected_in_scope = test.get("expected_in_scope", True)
        expected_contains = test.get("expected_answer_contains", [])

        r = requests.post(f"{base_url}/api/policy/ask", json={"question": q})
        r.raise_for_status()
        data = r.json()

        in_scope = data["is_in_scope"]
        answer = data["answer"].lower()

        scope_ok = in_scope == expected_in_scope
        content_ok = all(term.lower() in answer for term in expected_contains)

        total += 1
        if scope_ok:
            correct_scope += 1

        status = "OK" if scope_ok else "WRONG"
        print(
            f"  Q: {q[:60]}... → in_scope={in_scope} (expected={expected_in_scope}) {status}"
        )
        if expected_contains and not content_ok:
            print(f"    CONTENT MISS: expected one of {expected_contains} in answer")

    return {
        "scope_accuracy": correct_scope / total if total else 0,
        "total_qa_tests": total,
    }


def main():
    parser = argparse.ArgumentParser(description="Northwind Expense Review — Eval Harness")
    parser.add_argument("--expected", required=True, help="Path to expected outcomes JSON")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()

    with open(args.expected) as f:
        expected = json.load(f)

    print("=" * 60)
    print("Northwind Expense Review — Evaluation")
    print(f"Target: {args.base_url}")
    print("=" * 60)

    results: dict = {}

    if expected.get("submissions"):
        print("\n--- Submission Verdicts ---")
        results["submissions"] = eval_submissions(args.base_url, expected["submissions"])

    if expected.get("qa_tests"):
        print("\n--- Policy Q&A ---")
        results["qa"] = eval_qa(args.base_url, expected["qa_tests"])

    print("\n" + "=" * 60)
    print("METRICS SUMMARY")
    print("=" * 60)

    if "submissions" in results:
        m = results["submissions"]
        print(f"Verdict accuracy:          {m['verdict_accuracy']:.1%}")
        print(f"Citation rate:             {m['citation_rate']:.1%}")
        print(f"Low-conf wrong rate:       {m['low_confidence_wrong_rate']:.1%}")

    if "qa" in results:
        m = results["qa"]
        print(f"Q&A scope accuracy:        {m['scope_accuracy']:.1%}")

    print("=" * 60)

    out_path = "eval_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results written to {out_path}")


if __name__ == "__main__":
    main()
