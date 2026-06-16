import anthropic
from policy_loader import load_policies

client = anthropic.Anthropic()

REVIEW_TOOL = {
    "name": "submit_verdict",
    "description": "Submit a compliance verdict for this expense receipt.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["compliant", "flagged", "rejected", "needs_info"],
                "description": (
                    "compliant=passes all policies; "
                    "flagged=policy concern that needs human review; "
                    "rejected=clear policy violation, not reimbursable; "
                    "needs_info=cannot determine without more context"
                ),
            },
            "confidence": {
                "type": "number",
                "description": "0.0 to 1.0. Set below 0.7 when policy text is ambiguous or receipt is unclear.",
            },
            "reasoning": {
                "type": "string",
                "description": "Clear, specific explanation of why this verdict was reached. Reference amounts, caps, and policy rules explicitly.",
            },
            "policy_citations": {
                "type": "array",
                "description": "Every policy clause that informed this verdict. Must include verbatim quoted text.",
                "items": {
                    "type": "object",
                    "properties": {
                        "doc_id": {"type": "string", "description": "e.g. TEP-002"},
                        "section": {"type": "string", "description": "e.g. §2 or §3.1"},
                        "quoted_text": {"type": "string", "description": "Exact verbatim quote from the policy"},
                    },
                    "required": ["doc_id", "section", "quoted_text"],
                },
            },
            "reimbursable_amount": {
                "type": "number",
                "description": "Dollar amount eligible for reimbursement. May be less than total if partially non-compliant.",
            },
            "flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific issues identified, each as a short descriptive string.",
            },
        },
        "required": ["verdict", "confidence", "reasoning", "policy_citations", "reimbursable_amount"],
    },
}

SYSTEM_PROMPT = """You are a meticulous expense compliance reviewer for Northwind Logistics.

Your job is to review a single expense receipt against the full company policy library and return a structured verdict.

Rules you must follow:
1. Base every verdict ONLY on the provided policy text. Do not invent rules.
2. Every policy_citation must use exact verbatim quoted_text from the policies — no paraphrasing.
3. Use the employee's grade, trip context, and trip purpose to inform your review. Solo travel vs. client entertainment changes the applicable rules.
4. When a receipt is partially non-compliant (e.g., alcohol on a meal with food that is reimbursable), set reimbursable_amount to the compliant portion.
5. Set confidence below 0.7 when: the receipt is ambiguous, the policy is unclear, or the trip context is insufficient to make a determination. Use "needs_info" verdict if critical context is missing.
6. Do not flag items for which there is no clear policy basis. When in doubt about whether something violates policy, use "flagged" with low confidence rather than "rejected".
7. Check city tier (TEP-004 §3) for lodging and meal caps. High-cost city uplift (TEP-002 §2.3) is +25% for Tier 1 cities."""


def review_line_item(
    extracted: dict,
    employee: dict,
    trip_purpose: str,
    trip_dates: str,
) -> dict:
    policy_text = load_policies()

    user_message = f"""## Employee Context
- Name: {employee.get("name")}
- Grade: {employee.get("grade")} (per TEP-009, grade determines approval thresholds)
- Title: {employee.get("title")}
- Department: {employee.get("department")}
- Home base: {employee.get("home_base")}

## Trip Context
- Purpose: {trip_purpose}
- Dates: {trip_dates}

## Receipt to Review
{_format_receipt(extracted)}

## Full Policy Library
{policy_text}

Review this receipt for compliance. Apply all relevant policies. If the receipt involves meals, check both TEP-002 (meal caps) and TEP-003 (alcohol). If lodging, apply TEP-004 city tier caps. If transport, apply TEP-006."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        tools=[REVIEW_TOOL],
        tool_choice={"type": "tool", "name": "submit_verdict"},
        messages=[{"role": "user", "content": user_message}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_verdict":
            result = dict(block.input)
            result.setdefault("flags", [])
            return result

    raise RuntimeError("Claude did not return a submit_verdict tool call")


def _format_receipt(extracted: dict) -> str:
    lines = [
        f"- Merchant: {extracted.get('merchant', 'Unknown')}",
        f"- Date: {extracted.get('date', 'Unknown')}",
        f"- Total Amount: ${extracted.get('total_amount', 0):.2f}",
        f"- Category: {extracted.get('category', 'Unknown')}",
    ]
    if extracted.get("meal_type"):
        lines.append(f"- Meal Type: {extracted['meal_type']}")
    if extracted.get("city"):
        lines.append(f"- City: {extracted['city']}")
    if extracted.get("nights"):
        lines.append(f"- Nights: {extracted['nights']}")
    if extracted.get("alcohol_present"):
        lines.append(f"- Alcohol Present: Yes (${extracted.get('alcohol_amount', 0):.2f})")
    else:
        lines.append("- Alcohol Present: No")
    if extracted.get("attendees_mentioned"):
        lines.append(f"- Attendees Mentioned: {', '.join(extracted['attendees_mentioned'])}")
    if extracted.get("line_items"):
        lines.append("- Line Items:")
        for item in extracted["line_items"]:
            lines.append(f"    • {item.get('description', '')}: ${item.get('amount', 0):.2f}")
    if extracted.get("notes"):
        lines.append(f"- Notes: {extracted['notes']}")
    return "\n".join(lines)
