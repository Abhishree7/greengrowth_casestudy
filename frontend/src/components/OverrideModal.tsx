import { useState } from "react";
import { X } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";

const VERDICTS = ["compliant", "flagged", "rejected", "needs_info"] as const;

interface Props {
  lineItemId: number;
  submissionId: number;
  currentVerdict: string | null;
  onClose: () => void;
}

export function OverrideModal({ lineItemId, submissionId, currentVerdict, onClose }: Props) {
  const [newVerdict, setNewVerdict] = useState(currentVerdict ?? "compliant");
  const [comment, setComment] = useState("");
  const [reviewer, setReviewer] = useState("Finance Reviewer");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      api.overrideVerdict(lineItemId, {
        new_verdict: newVerdict,
        reviewer_comment: comment,
        reviewer,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["submission", submissionId] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">Override Verdict</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">New Verdict</label>
            <select
              value={newVerdict}
              onChange={(e) => setNewVerdict(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {VERDICTS.map((v) => (
                <option key={v} value={v}>
                  {v.charAt(0).toUpperCase() + v.slice(1).replace("_", " ")}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Reviewer Name</label>
            <input
              type="text"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Comment <span className="text-red-500">*</span>
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              placeholder="Explain the reason for this override..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          {mutation.isError && (
            <p className="text-red-600 text-sm">Failed to save override. Please try again.</p>
          )}

          <div className="flex gap-3 pt-1">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={() => mutation.mutate()}
              disabled={!comment.trim() || mutation.isPending}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {mutation.isPending ? "Saving..." : "Save Override"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
