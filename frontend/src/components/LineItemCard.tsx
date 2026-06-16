import { useState } from "react";
import { ChevronDown, ChevronUp, Quote, AlertTriangle } from "lucide-react";
import { VerdictBadge } from "./VerdictBadge";
import type { LineItem, Verdict } from "../types";

const BORDER: Record<string, string> = {
  compliant: "border-l-green-400",
  flagged: "border-l-yellow-400",
  rejected: "border-l-red-400",
  needs_info: "border-l-blue-400",
};

interface Props {
  item: LineItem;
  onOverride: (lineItemId: number) => void;
}

export function LineItemCard({ item, onOverride }: Props) {
  const [expanded, setExpanded] = useState(false);

  const effectiveVerdict: Verdict | null = item.override
    ? (item.override.new_verdict as Verdict)
    : item.verdict;

  const borderColor = BORDER[effectiveVerdict ?? ""] ?? "border-l-gray-300";

  return (
    <div className={`bg-white border border-gray-200 border-l-4 ${borderColor} rounded-lg overflow-hidden`}>
      {/* Header row */}
      <div className="flex items-center gap-4 px-4 py-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-sm text-gray-900 truncate">
              {item.merchant ?? item.receipt_filename}
            </span>
            {item.category && (
              <span className="text-xs text-gray-400 uppercase tracking-wide">
                {item.category}
                {item.extracted_data?.meal_type ? ` · ${item.extracted_data.meal_type}` : ""}
              </span>
            )}
          </div>
          <div className="flex gap-3 mt-0.5 text-xs text-gray-400">
            {item.date && <span>{item.date}</span>}
            {item.amount != null && <span>${item.amount.toFixed(2)}</span>}
            {item.reimbursable_amount != null && item.reimbursable_amount !== item.amount && (
              <span className="text-amber-600">reimb. ${item.reimbursable_amount.toFixed(2)}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <VerdictBadge verdict={effectiveVerdict} />
          {item.confidence != null && (
            <span className="text-xs text-gray-400">{Math.round(item.confidence * 100)}%</span>
          )}
          {item.verdict && (
            <button
              onClick={() => onOverride(item.id)}
              className="text-xs text-gray-400 hover:text-gray-700 underline"
            >
              Override
            </button>
          )}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-gray-400 hover:text-gray-600"
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-gray-100 px-4 py-3 space-y-4 text-sm">
          {/* Override banner */}
          {item.override && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs">
              <span className="font-semibold text-amber-800">Override by {item.override.reviewer}:</span>
              <span className="text-amber-700 ml-1">{item.override.reviewer_comment}</span>
              <span className="text-amber-400 ml-2">
                ({item.override.original_verdict} → {item.override.new_verdict})
              </span>
            </div>
          )}

          {/* Flags */}
          {item.flags && item.flags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {item.flags.map((flag, i) => (
                <span
                  key={i}
                  className="flex items-center gap-1 text-xs bg-red-50 text-red-700 border border-red-100 px-2.5 py-1 rounded-full"
                >
                  <AlertTriangle size={11} />
                  {flag}
                </span>
              ))}
            </div>
          )}

          {/* Reasoning */}
          {item.reasoning && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Reasoning
              </p>
              <p className="text-gray-700 leading-relaxed">{item.reasoning}</p>
            </div>
          )}

          {/* Policy citations */}
          {item.policy_citations && item.policy_citations.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Policy Citations
              </p>
              <div className="space-y-2">
                {item.policy_citations.map((c, i) => (
                  <div key={i} className="bg-gray-50 border border-gray-200 rounded p-3">
                    <div className="flex items-center gap-1.5 mb-1">
                      <Quote size={12} className="text-gray-400" />
                      <span className="text-xs font-semibold text-gray-600">
                        {c.doc_id} {c.section}
                      </span>
                    </div>
                    <p className="text-gray-600 text-xs italic leading-relaxed">"{c.quoted_text}"</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
