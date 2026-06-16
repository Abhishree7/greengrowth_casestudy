import base64
import os
import pdfplumber
import anthropic

client = anthropic.Anthropic()

EXTRACT_TOOL = {
    "name": "extract_receipt_data",
    "description": "Extract structured data from a receipt document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "merchant": {"type": "string", "description": "Vendor or merchant name"},
            "date": {"type": "string", "description": "Transaction date in YYYY-MM-DD format"},
            "total_amount": {"type": "number", "description": "Total charged amount in USD"},
            "category": {
                "type": "string",
                "enum": ["meal", "lodging", "transport", "conference", "other"],
            },
            "meal_type": {
                "type": "string",
                "enum": ["breakfast", "lunch", "dinner"],
                "description": "Required when category is 'meal'",
            },
            "city": {"type": "string", "description": "City where the expense occurred"},
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "amount": {"type": "number"},
                    },
                    "required": ["description", "amount"],
                },
            },
            "attendees_mentioned": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Any names or parties mentioned on the receipt",
            },
            "alcohol_present": {
                "type": "boolean",
                "description": "Whether alcohol charges appear on this receipt",
            },
            "alcohol_amount": {
                "type": "number",
                "description": "Total alcohol charges if present, else 0",
            },
            "nights": {
                "type": "integer",
                "description": "Number of nights for lodging receipts",
            },
            "notes": {
                "type": "string",
                "description": "Anything unusual or ambiguous on the receipt",
            },
        },
        "required": ["merchant", "date", "total_amount", "category", "alcohol_present", "alcohol_amount"],
    },
}

EXTRACT_PROMPT = """Extract all structured data from this receipt. Be precise with amounts.
If you cannot determine a field from the receipt, omit it rather than guessing.
For meal_type, infer from the time of day or meal description if not explicit."""


def extract_receipt(file_path: str) -> dict:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        text = _pdf_to_text(file_path)
        if len(text.strip()) > 50:
            return _extract_from_text(text, file_path)
        # Scanned PDF — fall through to vision
        return _extract_from_image(file_path, media_type="application/pdf")

    if ext in (".jpg", ".jpeg"):
        return _extract_from_image(file_path, media_type="image/jpeg")

    if ext == ".png":
        return _extract_from_image(file_path, media_type="image/png")

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return _extract_from_text(f.read(), file_path)

    raise ValueError(f"Unsupported file type: {ext}")


def _pdf_to_text(path: str) -> str:
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
    return "\n\n".join(pages)


def _extract_from_text(text: str, filename: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "extract_receipt_data"},
        messages=[
            {
                "role": "user",
                "content": f"{EXTRACT_PROMPT}\n\nFile: {os.path.basename(filename)}\n\nReceipt text:\n{text}",
            }
        ],
    )
    return _parse_tool_response(response)


def _extract_from_image(path: str, media_type: str) -> dict:
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "extract_receipt_data"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": data},
                    },
                    {"type": "text", "text": EXTRACT_PROMPT},
                ],
            }
        ],
    )
    return _parse_tool_response(response)


def _parse_tool_response(response) -> dict:
    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_receipt_data":
            return block.input
    raise RuntimeError("Claude did not return a tool_use block for receipt extraction")
