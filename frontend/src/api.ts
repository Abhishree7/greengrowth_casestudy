import axios from "axios";
import type {
  Employee,
  Submission,
  SubmissionSummary,
  LineItem,
  Override,
  PolicyAnswer,
} from "./types";

const http = axios.create({ baseURL: "/api" });

export const api = {
  // Employees
  listEmployees: (): Promise<Employee[]> =>
    http.get<Employee[]>("/employees").then((r) => r.data),

  createEmployee: (data: Omit<Employee, "id">): Promise<Employee> =>
    http.post<Employee>("/employees", data).then((r) => r.data),

  // Submissions
  createSubmission: (data: {
    employee_id: string;
    trip_purpose: string;
    trip_dates: string;
  }): Promise<Submission> =>
    http.post<Submission>("/submissions", data).then((r) => r.data),

  listSubmissions: (params?: {
    employee_id?: string;
    status?: string;
  }): Promise<SubmissionSummary[]> =>
    http.get<SubmissionSummary[]>("/submissions", { params }).then((r) => r.data),

  getSubmission: (id: number): Promise<Submission> =>
    http.get<Submission>(`/submissions/${id}`).then((r) => r.data),

  uploadReceipts: (submissionId: number, files: File[]): Promise<Submission> => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return http
      .post<Submission>(`/submissions/${submissionId}/receipts`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  reviewSubmission: (submissionId: number): Promise<Submission> =>
    http.post<Submission>(`/submissions/${submissionId}/review`).then((r) => r.data),

  // Overrides
  overrideVerdict: (
    lineItemId: number,
    data: { new_verdict: string; reviewer_comment: string; reviewer?: string }
  ): Promise<Override> =>
    http
      .patch<Override>(`/submissions/line-items/${lineItemId}/override`, data)
      .then((r) => r.data),

  // Policy Q&A
  askPolicy: (
    question: string,
    history: { role: string; content: string }[] = []
  ): Promise<PolicyAnswer> =>
    http.post<PolicyAnswer>("/policy/ask", { question, history }).then((r) => r.data),
};
