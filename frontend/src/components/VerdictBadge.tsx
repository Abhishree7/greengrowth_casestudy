import type { Verdict } from "../types";

const CONFIG: Record<
  Verdict,
  { label: string; className: string }
> = {
  compliant: { label: "Compliant", className: "bg-green-100 text-green-800" },
  flagged: { label: "Flagged", className: "bg-yellow-100 text-yellow-800" },
  rejected: { label: "Rejected", className: "bg-red-100 text-red-800" },
  needs_info: { label: "Needs Info", className: "bg-blue-100 text-blue-800" },
};

export function VerdictBadge({ verdict }: { verdict: Verdict | null }) {
  if (!verdict) return <span className="text-gray-400 text-xs">Pending</span>;
  const { label, className } = CONFIG[verdict] ?? CONFIG.needs_info;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${className}`}>
      {label}
    </span>
  );
}
