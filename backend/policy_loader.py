import os
import pdfplumber

POLICY_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "policies")

_policy_cache: str | None = None


def load_policies(force_reload: bool = False) -> str:
    global _policy_cache
    if _policy_cache is not None and not force_reload:
        return _policy_cache

    policy_dir = os.path.abspath(POLICY_DIR)
    if not os.path.isdir(policy_dir):
        raise RuntimeError(f"Policy directory not found: {policy_dir}")

    pdf_files = sorted(f for f in os.listdir(policy_dir) if f.endswith(".pdf"))
    if not pdf_files:
        raise RuntimeError(f"No PDF files found in {policy_dir}")

    sections: list[str] = []
    for filename in pdf_files:
        path = os.path.join(policy_dir, filename)
        text = _extract_pdf_text(path)
        if text.strip():
            sections.append(f"=== POLICY FILE: {filename} ===\n\n{text}")

    _policy_cache = "\n\n" + ("\n\n" + "=" * 60 + "\n\n").join(sections) + "\n\n"
    return _policy_cache


def _extract_pdf_text(path: str) -> str:
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)


def policy_word_count() -> int:
    text = load_policies()
    return len(text.split())
