import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ChevronRight, AlertTriangle } from "lucide-react";
import { api } from "../api";
import type { SubmissionSummary } from "../types";

export default function HistoryPage() {
  const navigate = useNavigate();
  const [filterEmployee, setFilterEmployee] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const { data: employees = [] } = useQuery({
    queryKey: ["employees"],
    queryFn: api.listEmployees,
  });

  const { data: submissions = [], isLoading } = useQuery({
    queryKey: ["submissions", filterEmployee, filterStatus],
    queryFn: () =>
      api.listSubmissions({
        employee_id: filterEmployee || undefined,
        status: filterStatus || undefined,
      }),
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Submission History</h1>
        <div className="flex gap-3">
          <select
            value={filterEmployee}
            onChange={(e) => setFilterEmployee(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All employees</option>
            {employees.map((e) => (
              <option key={e.employee_id} value={e.employee_id}>
                {e.name}
              </option>
            ))}
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All statuses</option>
            <option value="draft">Draft</option>
            <option value="reviewed">Reviewed</option>
          </select>
        </div>
      </div>

      {isLoading && <div className="text-gray-500 text-sm">Loading...</div>}

      {!isLoading && submissions.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <p>No submissions found.</p>
        </div>
      )}

      <div className="space-y-2">
        {submissions.map((sub) => (
          <SubmissionRow
            key={sub.id}
            sub={sub}
            onClick={() => navigate(`/submissions/${sub.id}`)}
          />
        ))}
      </div>
    </div>
  );
}

function SubmissionRow({
  sub,
  onClick,
}: {
  sub: SubmissionSummary;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 flex items-center gap-4 hover:border-gray-300 hover:shadow-sm transition-all text-left"
    >
      <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center text-xs font-medium text-gray-600 shrink-0">
        {sub.employee.name
          .split(" ")
          .map((n) => n[0])
          .join("")}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-900">{sub.employee.name}</span>
          <span className="text-xs text-gray-400">{sub.employee.title}</span>
        </div>
        <p className="text-xs text-gray-500 truncate mt-0.5">{sub.trip_purpose}</p>
        <p className="text-xs text-gray-400">{sub.trip_dates}</p>
      </div>

      <div className="shrink-0 text-right space-y-1">
        <div className="text-sm font-medium text-gray-900">
          ${sub.total_amount.toFixed(2)}
        </div>
        <div className="text-xs text-gray-400">
          {sub.line_item_count} receipt{sub.line_item_count !== 1 ? "s" : ""}
        </div>
      </div>

      <div className="shrink-0 flex flex-col items-end gap-1.5">
        <span
          className={`text-xs px-2 py-0.5 rounded-full ${
            sub.status === "reviewed"
              ? "bg-green-100 text-green-700"
              : "bg-gray-100 text-gray-500"
          }`}
        >
          {sub.status}
        </span>
        {sub.flagged_count > 0 && (
          <span className="flex items-center gap-1 text-xs text-red-600">
            <AlertTriangle size={11} />
            {sub.flagged_count} issue{sub.flagged_count !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      <ChevronRight size={16} className="text-gray-300 shrink-0" />
    </button>
  );
}
