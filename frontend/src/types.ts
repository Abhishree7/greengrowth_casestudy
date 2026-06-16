export interface Employee {
  id: number;
  employee_id: string;
  name: string;
  grade: number;
  title: string | null;
  department: string | null;
  manager_id: string | null;
  home_base: string | null;
}

export interface PolicyCitation {
  doc_id: string;
  section: string;
  quoted_text: string;
}

export interface Override {
  id: number;
  original_verdict: string;
  new_verdict: string;
  reviewer_comment: string;
  reviewer: string;
  created_at: string;
}

export type Verdict = "compliant" | "flagged" | "rejected" | "needs_info";

export interface LineItem {
  id: number;
  receipt_filename: string;
  category: string | null;
  merchant: string | null;
  amount: number | null;
  date: string | null;
  verdict: Verdict | null;
  confidence: number | null;
  reasoning: string | null;
  policy_citations: PolicyCitation[] | null;
  reimbursable_amount: number | null;
  flags: string[] | null;
  extracted_data: Record<string, unknown> | null;
  override: Override | null;
  created_at: string;
}

export interface Submission {
  id: number;
  employee_id: string;
  trip_purpose: string | null;
  trip_dates: string | null;
  status: "draft" | "reviewing" | "reviewed";
  total_amount: number;
  reimbursable_amount: number;
  created_at: string;
  employee: Employee;
  line_items: LineItem[];
}

export interface SubmissionSummary {
  id: number;
  employee_id: string;
  trip_purpose: string | null;
  trip_dates: string | null;
  status: string;
  total_amount: number;
  reimbursable_amount: number;
  created_at: string;
  employee: Employee;
  line_item_count: number;
  flagged_count: number;
}

export interface PolicyAnswer {
  answer: string;
  citations: PolicyCitation[];
  is_in_scope: boolean;
}
