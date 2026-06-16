import { useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Upload, Play, Plus, Check, User } from "lucide-react";
import { api } from "../api";
import type { Employee } from "../types";
import { LineItemCard } from "../components/LineItemCard";
import { OverrideModal } from "../components/OverrideModal";
import { VerdictBadge } from "../components/VerdictBadge";

export default function SubmissionsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [selectedEmployee, setSelectedEmployee] = useState<Employee | null>(null);
  const [tripPurpose, setTripPurpose] = useState("");
  const [tripDates, setTripDates] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [overrideLineItemId, setOverrideLineItemId] = useState<number | null>(null);
  const [showNewEmployee, setShowNewEmployee] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: employees = [] } = useQuery({
    queryKey: ["employees"],
    queryFn: api.listEmployees,
  });

  const { data: submission, isLoading: loadingSub } = useQuery({
    queryKey: ["submission", Number(id)],
    queryFn: () => api.getSubmission(Number(id)),
    enabled: !!id,
    refetchInterval: (data) =>
      data?.state?.data?.status === "reviewing" ? 3000 : false,
  });

  const createSub = useMutation({
    mutationFn: api.createSubmission,
    onSuccess: (sub) => {
      queryClient.invalidateQueries({ queryKey: ["submissions"] });
      navigate(`/submissions/${sub.id}`);
    },
  });

  const uploadMut = useMutation({
    mutationFn: ({ subId, files }: { subId: number; files: File[] }) =>
      api.uploadReceipts(subId, files),
    onSuccess: () => {
      setFiles([]);
      queryClient.invalidateQueries({ queryKey: ["submission", Number(id)] });
    },
  });

  const reviewMut = useMutation({
    mutationFn: api.reviewSubmission,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["submission", Number(id)] }),
  });

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const dropped = Array.from(e.dataTransfer.files);
    setFiles((prev) => [...prev, ...dropped]);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) setFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
  }

  async function handleCreateSubmission() {
    if (!selectedEmployee || !tripPurpose || !tripDates) return;
    createSub.mutate({
      employee_id: selectedEmployee.employee_id,
      trip_purpose: tripPurpose,
      trip_dates: tripDates,
    });
  }

  const overrideItem = overrideLineItemId
    ? submission?.line_items.find((li) => li.id === overrideLineItemId)
    : null;

  if (id && loadingSub) {
    return <div className="text-gray-500 mt-8 text-center">Loading submission...</div>;
  }

  if (id && submission) {
    const unreviewed = submission.line_items.filter((li) => !li.verdict);
    const isReviewing = submission.status === "reviewing";

    return (
      <div className="space-y-6">
        {/* Submission header */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <User size={16} className="text-gray-400" />
                <span className="font-semibold text-gray-900">
                  {submission.employee.name}
                </span>
                <span className="text-xs text-gray-400">
                  Grade {submission.employee.grade} · {submission.employee.title}
                </span>
              </div>
              <p className="text-sm text-gray-600">{submission.trip_purpose}</p>
              <p className="text-xs text-gray-400 mt-0.5">{submission.trip_dates}</p>
            </div>
            <div className="text-right">
              <div className="text-lg font-semibold text-gray-900">
                ${submission.total_amount.toFixed(2)}
              </div>
              {submission.reimbursable_amount !== submission.total_amount && (
                <div className="text-sm text-amber-600">
                  Reimb. ${submission.reimbursable_amount.toFixed(2)}
                </div>
              )}
              <span
                className={`text-xs px-2 py-0.5 rounded-full mt-1 inline-block ${
                  submission.status === "reviewed"
                    ? "bg-green-100 text-green-700"
                    : submission.status === "reviewing"
                    ? "bg-yellow-100 text-yellow-700"
                    : "bg-gray-100 text-gray-600"
                }`}
              >
                {submission.status}
              </span>
            </div>
          </div>

          {/* Upload more receipts */}
          {submission.status !== "reviewing" && (
            <div className="mt-4 border-t border-gray-100 pt-4 space-y-3">
              <div
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
                  dragging ? "border-blue-400 bg-blue-50" : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <Upload size={18} className="mx-auto text-gray-400 mb-1" />
                <p className="text-sm text-gray-500">
                  Drop receipts here or click to browse
                </p>
                <p className="text-xs text-gray-400 mt-0.5">PDF, JPG, PNG, TXT</p>
                <input
                  ref={fileRef}
                  type="file"
                  multiple
                  accept=".pdf,.jpg,.jpeg,.png,.txt"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>

              {files.length > 0 && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">
                    {files.length} file(s) ready
                  </span>
                  <button
                    onClick={() => uploadMut.mutate({ subId: submission.id, files })}
                    disabled={uploadMut.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 text-white rounded-lg text-sm disabled:opacity-50"
                  >
                    <Check size={14} />
                    {uploadMut.isPending ? "Uploading..." : "Upload"}
                  </button>
                </div>
              )}

              {unreviewed.length > 0 && (
                <button
                  onClick={() => reviewMut.mutate(submission.id)}
                  disabled={reviewMut.isPending || isReviewing}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                >
                  <Play size={14} />
                  {reviewMut.isPending || isReviewing
                    ? "Running AI Review..."
                    : `Run AI Review (${unreviewed.length} receipt${unreviewed.length > 1 ? "s" : ""})`}
                </button>
              )}
            </div>
          )}

          {isReviewing && (
            <p className="mt-3 text-sm text-yellow-700 animate-pulse">
              AI review in progress — this may take a minute...
            </p>
          )}
        </div>

        {/* Line items */}
        <div className="space-y-3">
          {submission.line_items.map((item) => (
            <LineItemCard
              key={item.id}
              item={item}
              onOverride={setOverrideLineItemId}
            />
          ))}
        </div>

        {/* Summary */}
        {submission.status === "reviewed" && (
          <div className="bg-white border border-gray-200 rounded-xl p-4 flex gap-6 text-sm">
            {(["compliant", "flagged", "rejected", "needs_info"] as const).map(
              (v) => {
                const count = submission.line_items.filter(
                  (li) =>
                    (li.override?.new_verdict ?? li.verdict) === v
                ).length;
                return count > 0 ? (
                  <div key={v} className="flex items-center gap-2">
                    <VerdictBadge verdict={v} />
                    <span className="text-gray-600">{count}</span>
                  </div>
                ) : null;
              }
            )}
          </div>
        )}

        {overrideItem && (
          <OverrideModal
            lineItemId={overrideItem.id}
            submissionId={submission.id}
            currentVerdict={overrideItem.override?.new_verdict ?? overrideItem.verdict}
            onClose={() => setOverrideLineItemId(null)}
          />
        )}
      </div>
    );
  }

  // New submission form
  return (
    <div className="max-w-xl mx-auto space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">New Submission</h1>

      {/* Employee selection */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
        <h2 className="font-medium text-gray-800">Select Employee</h2>
        <div className="grid grid-cols-1 gap-2 max-h-56 overflow-y-auto pr-1">
          {employees.map((emp) => (
            <button
              key={emp.employee_id}
              onClick={() => setSelectedEmployee(emp)}
              className={`flex items-start gap-3 p-3 rounded-lg border text-left transition-colors ${
                selectedEmployee?.employee_id === emp.employee_id
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-xs font-medium text-gray-600 shrink-0">
                {emp.name.split(" ").map((n) => n[0]).join("")}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">{emp.name}</p>
                <p className="text-xs text-gray-500">
                  {emp.title} · Grade {emp.grade}
                </p>
              </div>
            </button>
          ))}
        </div>

        <button
          onClick={() => setShowNewEmployee((v) => !v)}
          className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800"
        >
          <Plus size={14} />
          Add new employee
        </button>

        {showNewEmployee && (
          <NewEmployeeForm
            onCreated={(emp) => {
              queryClient.invalidateQueries({ queryKey: ["employees"] });
              setSelectedEmployee(emp);
              setShowNewEmployee(false);
            }}
          />
        )}
      </div>

      {/* Trip details */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
        <h2 className="font-medium text-gray-800">Trip Details</h2>
        <div>
          <label className="block text-sm text-gray-600 mb-1">Purpose</label>
          <input
            type="text"
            value={tripPurpose}
            onChange={(e) => setTripPurpose(e.target.value)}
            placeholder="e.g. Quarterly client review with Acme Corp"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">Dates</label>
          <input
            type="text"
            value={tripDates}
            onChange={(e) => setTripDates(e.target.value)}
            placeholder="e.g. 2025-04-14 to 2025-04-16"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <button
        onClick={handleCreateSubmission}
        disabled={!selectedEmployee || !tripPurpose || !tripDates || createSub.isPending}
        className="w-full py-3 bg-blue-600 text-white rounded-xl font-medium text-sm hover:bg-blue-700 disabled:opacity-50"
      >
        {createSub.isPending ? "Creating..." : "Create Submission"}
      </button>
    </div>
  );
}

function NewEmployeeForm({ onCreated }: { onCreated: (emp: Employee) => void }) {
  const [form, setForm] = useState({
    employee_id: "",
    name: "",
    grade: 3,
    title: "",
    department: "",
    home_base: "",
  });

  const mutation = useMutation({
    mutationFn: () => api.createEmployee({ ...form, manager_id: null }),
    onSuccess: onCreated,
  });

  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-3 bg-gray-50">
      <p className="text-xs font-medium text-gray-600">New Employee</p>
      {(
        [
          ["employee_id", "Employee ID"],
          ["name", "Full Name"],
          ["title", "Title"],
          ["department", "Department"],
          ["home_base", "Home Base"],
        ] as [keyof typeof form, string][]
      ).map(([key, label]) => (
        <input
          key={key}
          type="text"
          placeholder={label}
          value={form[key]}
          onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
          className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
        />
      ))}
      <div>
        <label className="text-xs text-gray-500">Grade</label>
        <input
          type="number"
          min={1}
          max={12}
          value={form.grade}
          onChange={(e) => setForm((f) => ({ ...f, grade: Number(e.target.value) }))}
          className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-1"
        />
      </div>
      <button
        onClick={() => mutation.mutate()}
        disabled={!form.employee_id || !form.name || mutation.isPending}
        className="w-full py-1.5 bg-gray-900 text-white rounded text-sm disabled:opacity-50"
      >
        {mutation.isPending ? "Adding..." : "Add Employee"}
      </button>
      {mutation.isError && (
        <p className="text-red-600 text-xs">Failed to add employee.</p>
      )}
    </div>
  );
}
