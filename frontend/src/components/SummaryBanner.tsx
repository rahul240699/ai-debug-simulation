/** Summary banner — answers "What was the root cause of failure?" */

import type { DiagnosisSummary } from "@/lib/types";

interface Props {
  summary: DiagnosisSummary;
  win: boolean;
}

const CATEGORY_LABELS: Record<string, string> = {
  stale_info: "Stale Information",
  dm_oracle: "DM Oracle Decay",
  coordination: "Coordination Gap",
  tool_failure: "Tool Failure",
};

const CATEGORY_COLORS: Record<string, string> = {
  stale_info: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  dm_oracle: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  coordination: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  tool_failure: "bg-red-500/10 text-red-400 border-red-500/20",
};

export function SummaryBanner({ summary, win }: Props) {
  return (
    <div
      className={`rounded-lg border p-5 mb-6 ${
        win
          ? "bg-emerald-500/5 border-emerald-500/20"
          : "bg-red-500/5 border-red-500/20"
      }`}
    >
      <div className="flex items-start gap-3">
        <div className={`mt-0.5 text-lg ${win ? "text-emerald-400" : "text-red-400"}`}>
          {win ? "✓" : "✕"}
        </div>
        <div className="flex-1">
          <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide mb-2">
            Root Cause Analysis
          </h2>
          <p className="text-sm text-zinc-300 leading-relaxed">{summary.root_cause}</p>
          {summary.failure_categories.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {summary.failure_categories.map((fc) => (
                <span
                  key={fc.category}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${
                    CATEGORY_COLORS[fc.category] ?? "bg-zinc-800 text-zinc-400 border-zinc-700"
                  }`}
                >
                  {CATEGORY_LABELS[fc.category] ?? fc.category}
                  <span className="opacity-60">×{fc.count}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
