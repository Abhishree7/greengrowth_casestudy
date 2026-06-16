# Northwind Expense Review — AI-Assisted Pre-Review System

> **Live demo:** https://greengrowthcasestudy-production.up.railway.app

An AI-powered expense receipt pre-review system for Northwind Logistics. Employees submit expense receipts; the system extracts structured data, checks every item against the full company T&E policy library, and surfaces a verdict (`compliant` / `flagged` / `rejected` / `needs_info`) with verbatim policy citations. Human reviewers make the final call and can override any AI verdict with a logged reason.

---

## Running Locally

### Prerequisites

- Python 3.11+
- Node 20+
- An [Anthropic API key](https://console.anthropic.com/)

### 1. Clone and configure

```bash
git clone https://github.com/Abhishree7/greengrowth_casestudy.git
cd greengrowth_casestudy

cp .env.example .env
# Edit .env and set:
#   ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Backend

```bash
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

The server seeds employees from `data/submissions/*/employee_info.json` and loads all policy PDFs from `data/policies/` on first startup.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev        # dev server at http://localhost:5173
# or
npm run build      # production build served by the FastAPI backend at http://localhost:8000
```

### 4. Evaluation harness

```bash
pip install requests   # if not already installed
python eval.py --expected expected.json --base-url http://localhost:8000
```

See [Evaluation Harness](#evaluation-harness) below for the expected JSON schema.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Browser (React + Vite)                        │
│                                                                      │
│  SubmissionsPage  ──────────────────────────  PolicyPage (Q&A chat) │
│  (upload, review, override)                   (conversation history) │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ HTTP (JSON)
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                                 │
│                                                                      │
│  POST /api/submissions/{id}/receipts   ← file upload                │
│  POST /api/submissions/{id}/review     ← triggers AI pipeline       │
│  PATCH /api/submissions/line-items/{id}/override                     │
│  POST /api/policy/ask                  ← Q&A with history           │
│  GET  /health                          ← Railway healthcheck        │
│                                                                      │
│  ┌──────────────────────┐  ┌──────────────────────────────────────┐ │
│  │   receipt_extractor  │  │          review_engine               │ │
│  │                      │  │                                      │ │
│  │  PDF → pdfplumber    │  │  Full policy text (~40k tokens)      │ │
│  │  image/scan → vision │  │  + employee grade + trip context     │ │
│  │  txt → read directly │  │  → Claude claude-sonnet-4-6 tool_use      │ │
│  │                      │  │  → verdict + citations + amount      │ │
│  │  → tool_use JSON     │  │                                      │ │
│  └──────────────────────┘  └──────────────────────────────────────┘ │
│                                                                      │
│  SQLAlchemy / SQLite                                                 │
│  employees | submissions | line_items | overrides                    │
└──────────────────────────────────────────────────────────────────────┘
                            │
                    Anthropic API
               (claude-sonnet-4-6, tool_use)
```

### Data model

| Table | Purpose |
|---|---|
| `employees` | Grade, title, department, home base — used to look up spending caps |
| `submissions` | One trip per submission; status: `draft → reviewing → reviewed` |
| `line_items` | One row per receipt; stores extracted JSON, verdict, citations, reimbursable amount |
| `overrides` | Immutable audit trail; preserves original AI verdict alongside reviewer's decision |

### Two-stage AI pipeline

Every receipt passes through two sequential Claude calls:

**Stage 1 — Extraction** (`receipt_extractor.py`)  
Reads the file, sends it to Claude with a `tool_choice`-forced JSON schema, and returns structured fields: merchant, date, total amount, category, meal type, city, line items, alcohol present/amount, nights, attendees.

**Stage 2 — Compliance review** (`review_engine.py`)  
Sends the extracted fields + full policy library + employee context + trip purpose to Claude. Returns: verdict, confidence (0–1), plain-prose reasoning, verbatim policy citations (`doc_id`, `section`, `quoted_text`), reimbursable amount, and a flags array.

Both stages use `tool_choice={"type": "tool", "name": "..."}` — Claude is forced to return structured JSON; there is no free-text parsing.

---

## Design Choices and Tradeoffs

### No RAG — full policy text in every call

The policy library is ~8 PDFs totalling roughly 154 kB / 40k tokens. That fits comfortably inside Claude's 200k-token context. RAG was considered and rejected for three reasons:

1. **Cross-references matter.** Northwind's policies cite each other frequently (e.g., TEP-002 §2.3 references TEP-004's city tier table for meal cap uplifts). Chunked retrieval would fetch one policy section without its dependencies and produce wrong verdicts.
2. **Recall is all-or-nothing.** A missed retrieval chunk causes a silent wrong verdict. A missed sentence in a 40k-token context is far less likely, and Claude has been shown to handle faithful recall at this size reliably.
3. **Latency and cost at this scale are acceptable.** Loading 40k tokens adds ~0.3s and ~$0.12 per review call. The accuracy benefit outweighs the marginal cost.

The tradeoff: if the policy library grows past ~80k tokens, this approach becomes expensive. At that scale, a two-tier approach — keyword-filtered retrieval followed by full-section inclusion — would be the right next step.

### Model selection — claude-sonnet-4-6 for both stages

`claude-sonnet-4-6` was chosen because it combines:
- **200k-token context** — required for full-policy review
- **Native vision** — required for image receipts and scanned PDFs that produce no extractable text
- **Reliable tool_use JSON** — critical because both stages require perfectly structured output

Claude Haiku was considered for the extraction stage (where the context is small and vision is sometimes needed). It would reduce extraction cost ~10×. The risk is that Haiku is more likely to mis-classify edge cases (e.g., inferring meal type from time-of-day cues). For a pre-review system where false negatives reach a human anyway, this tradeoff is reasonable and would be worth enabling as a cost-saving option.

### Vision model — when it activates

The extractor routes by file type:
- **PDF with extractable text** → pdfplumber → text prompt (faster, cheaper)
- **Image receipt (.jpg, .png)** → base64-encoded → Claude vision
- **Scanned PDF** (pdfplumber returns <50 chars) → falls through to Claude vision
- **Plain text (.txt)** → read directly → text prompt

Vision adds ~50% latency and cost to extraction. It's only triggered when text extraction fails, not by default.

### Confidence and when to flag vs. reject vs. ask a human

The review engine uses four verdicts:

| Verdict | When to use |
|---|---|
| `compliant` | Receipt clearly satisfies all applicable policies |
| `flagged` | Policy concern that needs human eyes — e.g., amount is close to a cap, context is borderline, or the policy is ambiguous |
| `rejected` | Clear policy violation — e.g., alcohol charge on a non-client-entertainment meal, lodging that exceeds the city cap with no exception |
| `needs_info` | Critical context is missing to make any determination (no city listed for a hotel, no attendees listed for a client dinner) |

The system prompt instructs Claude to set `confidence < 0.7` when the receipt or policy is ambiguous, and to prefer `flagged` over `rejected` when doubt exists. The intent is to minimize false rejections: it is always better to surface uncertainty to a human reviewer than to automatically reject a legitimate expense.

The `reimbursable_amount` field allows partial compliance — a dinner receipt that includes $40 of food and $30 of alcohol returns `reimbursable_amount = 40`, not `0`.

### Human override and audit trail

Every override is persisted as an immutable `Override` row that stores both the original AI verdict and the reviewer's new verdict, along with a required comment and reviewer name. This creates an audit trail that can be used to:
- Identify systematic AI errors (same receipt type is always overridden → update prompt or policy wording)
- Hold reviewers accountable for their changes
- Train future models on human-corrected examples

### Policy Q&A session management

The Q&A chat sends the full conversation history to the backend on every turn. The backend injects the policy text **only into the first user message**, so it stays in Anthropic's prompt cache across follow-up questions. This avoids maintaining server-side session state while still getting cache efficiency for multi-turn conversations.

---

## Cost Estimation and Scaling

### Cost per submission (current)

| Stage | Model | Approx. input tokens | Approx. output tokens | Cost per receipt |
|---|---|---|---|---|
| Extraction | claude-sonnet-4-6 | ~1,000 | ~200 | ~$0.006 |
| Review | claude-sonnet-4-6 | ~41,000 | ~600 | ~$0.132 |
| **Total** | | | | **~$0.14 per receipt** |

Pricing: $3/MTok input, $15/MTok output (claude-sonnet-4-6 as of mid-2026).

A typical submission has 3–5 receipts, putting **cost per submission at ~$0.42–$0.70**.

### Prompt caching (biggest single lever)

The policy text (~40k tokens) is identical across every review call. Enabling Anthropic's prompt caching (`cache_control` breakpoints) reduces those tokens from $3/MTok to $0.30/MTok on cache reads:

| | No caching | With caching |
|---|---|---|
| Policy tokens cost/receipt | $0.12 | $0.012 |
| Per submission (4 receipts) | ~$0.56 | ~$0.13 |
| 10k submissions/day | ~$5,600/day | ~$1,300/day |

### Scaling to 10,000 submissions/day

At 10k submissions/day (~35k receipts) the current single-process synchronous architecture becomes a bottleneck. The path to scale:

1. **Add prompt caching** — immediate 4–5× cost reduction, no architectural change.
2. **Replace synchronous review with a task queue** — Celery + Redis; review jobs run in worker processes rather than blocking the HTTP request. The frontend already polls for `status=reviewing`, so the API contract is compatible.
3. **Swap SQLite for PostgreSQL** — SQLite has a single-writer lock; Postgres handles concurrent workers correctly.
4. **Add persistent file storage (S3/GCS)** — uploaded receipts are currently written to local disk, which doesn't survive container restarts or scale horizontally.
5. **Use the Anthropic Batch API** for non-urgent reviews — 50% cost reduction with up to 24h latency. Suitable for overnight processing of bulk submissions.
6. **Consider Haiku for extraction** — if the 40k-token review call is the bottleneck, moving extraction to Haiku saves time and cost on that stage.
7. **Horizontal scaling** — multiple FastAPI workers behind a load balancer; all state is in Postgres + S3, so workers are stateless.

---

## What I'd Do Next

**Prompt caching** — Adding `cache_control: {"type": "ephemeral"}` to the policy block in the review call is a one-hour change that cuts cost by ~80%. It's the highest-ROI improvement.

**Async review pipeline** — Move receipt processing to a Celery queue. The frontend already polls; the backend API contract doesn't change.

**Feedback loop from overrides** — When a reviewer overrides an AI verdict, log the original receipt, AI reasoning, and the correction. After 50–100 examples, use them as few-shot examples in the review prompt to steer the model toward the reviewer's reasoning patterns.

**Structured citation verification** — The system currently trusts that Claude's `quoted_text` is verbatim. Add a post-processing step that checks whether each quoted string is a substring of the actual policy text, and downgrades `confidence` if not.

**Support for multi-receipt meals** — When multiple receipts belong to the same client dinner, the per-person cap applies to the total, not each receipt individually. The current model checks each receipt in isolation.

**Richer eval dataset** — The eval harness is ready; the bottleneck is test cases. I'd create 20–30 labeled receipts covering: exact-cap edge cases, alcohol-mixed meals, multi-city trips, grade-based approval thresholds, and out-of-policy requests.

---

## Evaluation Harness

`eval.py` is a standalone script that exercises the live system against a provided JSON file of expected outcomes and prints a metrics summary.

### Usage

```bash
python eval.py --expected expected.json --base-url http://localhost:8000
# or against the deployed instance:
python eval.py --expected expected.json --base-url https://your-railway-url.railway.app
```

### Input schema

```json
{
  "submissions": [
    {
      "submission_folder": "01_clean_denver",
      "employee_id": "NW-04821",
      "trip_purpose": "Client site visit",
      "trip_dates": "2024-11-04 to 2024-11-06",
      "expected_verdicts": {
        "01_united_airlines.pdf": "compliant",
        "02_marriott_denver.pdf": "compliant",
        "03_dinner_with_client.pdf": "flagged"
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
```

`submission_folder` maps to a directory under `data/submissions/`. Each folder must contain `employee_info.json` and a `receipts/` subdirectory.

### Metrics

| Metric | What it measures | Why it matters |
|---|---|---|
| **Verdict accuracy** | `correct / total` over all receipts with expected labels | Primary signal: is the AI right? |
| **Citation rate** | Fraction of verdicts that include at least one policy citation | Measures groundedness — a correct verdict with no citation cannot be audited |
| **Low-confidence wrong rate** | Of wrong verdicts, what fraction had `confidence < 0.7` | Measures calibration — a well-calibrated model should signal uncertainty when it's wrong |
| **Q&A scope accuracy** | `correct scope label / total Q&A tests` | Measures refusal quality — the bot should neither answer out-of-scope questions nor refuse in-scope ones |

The harness writes full per-submission results to `eval_results.json`.

**Why these metrics and not others:**

- *Precision / recall by verdict class* would be the next addition once the test set is large enough (≥50 receipts per class).
- *Citation correctness* (does the quoted text actually appear in the policy?) is not yet automated but is the most important qualitative signal; a reviewer should spot-check a random sample.
- *Latency per receipt* is tracked implicitly (the review endpoint has a 300s timeout) but not yet reported. At scale, p99 latency matters as much as accuracy.
