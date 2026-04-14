/** Summary banner — answers "What was the root cause of failure?"
 *  RCA badges are clickable to filter the Divergence Timeline.
 */

import type { DiagnosisSummary } from "@/lib/types";

interface Props {
  summary: DiagnosisSummary;
  win: boolean;
  activeFilter?: string | null;
  onFilterCategory?: (category: string | null) => void;
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
  tool_failure: "bg-rose-500/10 text-rose-400 border-rose-500/20",
};

// Map failure categories to timeline event types they correspond to
const CATEGORY_TO_EVENT_TYPE: Record<string, string[]> = {
  stale_info: ["critical_divergence"],
  dm_oracle: ["dm_oracle"],
  coordination: ["coordination", "critical_divergence"],
  tool_failure: ["critical_divergence"],
};

export { CATEGORY_TO_EVENT_TYPE };

export function SummaryBanner({ summary, win, activeFilter, onFilterCategory }: Props) {
  return (
    <div
      className={`rounded-lg border p-5 mb-6 transition-colors duration-300 ${
        win
          ? "bg-emerald-500/5 border-emerald-500/20"
          : "bg-rose-500/5 border-rose-600/20"
      }`}
    >
      <div className="flex items-start gap-3">
        <div className={`mt-0.5 text-lg ${win ? "text-emerald-400" : "text-rose-400"}`}>
          {win ? "✓" : "✕"}
        </div>
        <div className="flex-1">
          <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide mb-2">
            Root Cause Analysis
          </h2>
          <p className="text-sm text-zinc-300 leading-relaxed">{summary.root_cause}</p>
          {summary.failure_categories.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {summary.failure_categories.map((fc) => {
                const isActive = activeFilter === fc.category;
                return (
                  <button
                    key={fc.category}
                    onClick={() => onFilterCategory?.(isActive ? null : fc.category)}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border transition-all duration-200 cursor-pointer ${
                      CATEGORY_COLORS[fc.category] ?? "bg-zinc-800 text-zinc-400 border-zinc-700"
                    } ${isActive ? "ring-2 ring-white/20 scale-105" : "hover:scale-[1.03]"}`}
                    title={`Click to ${isActive ? "clear" : "filter timeline by"} ${CATEGORY_LABELS[fc.category] ?? fc.category}`}
                  >
                    {CATEGORY_LABELS[fc.category] ?? fc.category}
                    <span className="opacity-60">×{fc.count}</span>
                  </button>
                );
              })}
              {activeFilter && (
                <button
                  onClick={() => onFilterCategory?.(null)}
                  className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors ml-1"
                >
                  Clear filter
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
