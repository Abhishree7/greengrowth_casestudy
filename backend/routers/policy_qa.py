import anthropic
from fastapi import APIRouter
from policy_loader import load_policies
from schemas import PolicyQuestion, PolicyAnswer, PolicyCitation, ChatMessage

router = APIRouter(prefix="/policy", tags=["policy"])
client = anthropic.Anthropic()

QA_TOOL = {
    "name": "answer_policy_question",
    "description": "Answer a question about Northwind Logistics policies.",
    "input_schema": {
        "type": "object",
        "properties": {
            "is_in_scope": {
                "type": "boolean",
                "description": "True if the question is answerable from the policy library.",
            },
            "answer": {
                "type": "string",
                "description": "The answer, or a polite decline if out of scope.",
            },
            "citations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "doc_id": {"type": "string"},
                        "section": {"type": "string"},
                        "quoted_text": {"type": "string"},
                    },
                    "required": ["doc_id", "section", "quoted_text"],
                },
                "description": "Verbatim quotes from the policies that support the answer.",
            },
        },
        "required": ["is_in_scope", "answer", "citations"],
    },
}

SYSTEM_PROMPT = """You are a policy assistant for Northwind Logistics.

Rules:
1. Answer ONLY using the provided policy documents. Never fabricate rules or amounts.
2. Every citation must use exact verbatim quoted_text from the document.
3. If the question cannot be answered from the policies, set is_in_scope=false and politely decline.
4. Decline questions unrelated to Northwind Logistics T&E or corporate policies.
5. When multiple policies apply, cite all of them."""


@router.post("/ask", response_model=PolicyAnswer)
def ask_policy_question(payload: PolicyQuestion):
    policy_text = load_policies()

    # Build message thread: inject policy text only into the first user turn
    messages = _build_messages(payload.history, payload.question, policy_text)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        tools=[QA_TOOL],
        tool_choice={"type": "tool", "name": "answer_policy_question"},
        messages=messages,
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "answer_policy_question":
            data = block.input
            return PolicyAnswer(
                answer=data["answer"],
                is_in_scope=data["is_in_scope"],
                citations=[PolicyCitation(**c) for c in data.get("citations", [])],
            )

    raise RuntimeError("Claude did not return a policy answer")


def _build_messages(
    history: list[ChatMessage], question: str, policy_text: str
) -> list[dict]:
    """
    Reconstruct the Anthropic messages array from stored history.
    Policy text is injected once — into the first user message — so it stays
    in the prompt cache across follow-up turns.
    """
    if not history:
        return [{"role": "user", "content": f"{question}\n\n---\n\nPolicy Library:\n{policy_text}"}]

    messages: list[dict] = []
    for i, msg in enumerate(history):
        content = msg.content
        # Append policy text to the very first user turn so the model always has it
        if i == 0 and msg.role == "user":
            content = f"{content}\n\n---\n\nPolicy Library:\n{policy_text}"
        messages.append({"role": msg.role, "content": content})

    messages.append({"role": "user", "content": question})
    return messages
