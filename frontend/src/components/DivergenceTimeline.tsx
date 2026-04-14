/** Divergence Timeline — vertical timeline showing only critical events.
 *  Supports category filtering from clickable RCA badges.
 */

import type { CriticalEvent } from "@/lib/types";

interface Props {
  timeline: CriticalEvent[];
  selectedEvent: CriticalEvent | null;
  onSelectEvent: (event: CriticalEvent) => void;
  categoryFilter?: string | null;
}

const SEVERITY_STYLES: Record<string, { dot: string; border: string; bg: string }> = {
  green: {
    dot: "bg-emerald-400",
    border: "border-emerald-500/20 hover:border-emerald-500/40",
    bg: "bg-emerald-500/5",
  },
  yellow: {
    dot: "bg-amber-400",
    border: "border-amber-500/20 hover:border-amber-500/40",
    bg: "bg-amber-500/5",
  },
  red: {
    dot: "bg-rose-400",
    border: "border-rose-500/20 hover:border-rose-500/40",
    bg: "bg-rose-500/5",
  },
};

const TYPE_LABELS: Record<string, string> = {
  decision_point: "Decision",
  critical_divergence: "Divergence",
  dm_oracle: "DM Oracle",
  coordination: "Message",
};

const TYPE_ICONS: Record<string, string> = {
  decision_point: "◆",
  critical_divergence: "⚠",
  dm_oracle: "🔮",
  coordination: "💬",
};

// Map category filter to matching event types
const FILTER_MAP: Record<string, (evt: CriticalEvent) => boolean> = {
  stale_info: (evt) =>
    evt.event_type === "critical_divergence" &&
    (evt.headline.toLowerCase().includes("wall") ||
     evt.headline.toLowerCase().includes("stale") ||
     evt.headline.toLowerCase().includes("hidden")),
  dm_oracle: (evt) => evt.event_type === "dm_oracle",
  coordination: (evt) =>
    evt.event_type === "coordination" ||
    (evt.event_type === "critical_divergence" &&
     evt.headline.toLowerCase().includes("partner")),
  tool_failure: (evt) =>
    evt.event_type === "critical_divergence" &&
    (evt.headline.toLowerCase().includes("failed") ||
     evt.headline.toLowerCase().includes("failure")),
};

export function DivergenceTimeline({ timeline, selectedEvent, onSelectEvent, categoryFilter }: Props) {
  const filteredTimeline = categoryFilter && FILTER_MAP[categoryFilter]
    ? timeline.filter(FILTER_MAP[categoryFilter])
    : timeline;

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg">
      <div className="px-4 py-3 border-b border-slate-700/50">
        <h3 className="text-sm font-semibold text-zinc-300">Divergence Timeline</h3>
        <p className="text-xs text-zinc-500 mt-0.5">
          {filteredTimeline.length}{categoryFilter ? ` of ${timeline.length}` : ""} critical events · Click to inspect
          {categoryFilter && (
            <span className="ml-1 text-amber-400">
              (filtered)
            </span>
          )}
        </p>
      </div>
      <div className="max-h-[600px] overflow-y-auto">
        {filteredTimeline.map((evt, i) => {
          const styles = SEVERITY_STYLES[evt.severity] ?? SEVERITY_STYLES.yellow;
          const isSelected =
            selectedEvent?.turn_number === evt.turn_number &&
            selectedEvent?.agent_id === evt.agent_id;

          return (
            <button
              key={`${evt.turn_number}-${evt.agent_id}-${i}`}
              onClick={() => onSelectEvent(evt)}
              className={`w-full text-left px-4 py-3 border-b border-slate-700/30 transition-all duration-200 cursor-pointer ${
                isSelected ? `${styles.bg} border-l-2 ${styles.border}` : "hover:bg-slate-700/30"
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Timeline dot */}
                <div className="flex flex-col items-center pt-1">
                  <div className={`w-2.5 h-2.5 rounded-full ${styles.dot} transition-transform duration-200`} />
                  {i < filteredTimeline.length - 1 && (
                    <div className="w-px h-full bg-slate-700/50 mt-1" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  {/* Header row */}
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-mono text-zinc-500">T{evt.turn_number}</span>
                    <span
                      className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                        evt.agent_id === "agent_a"
                          ? "bg-blue-500/10 text-blue-400"
                          : "bg-orange-500/10 text-orange-400"
                      }`}
                    >
                      {evt.agent_id === "agent_a" ? "Agent A" : "Agent B"}
                    </span>
                    <span className="text-xs text-zinc-600">
                      {TYPE_ICONS[evt.event_type]} {TYPE_LABELS[evt.event_type]}
                    </span>
                  </div>

                  {/* Headline */}
                  <p className="text-sm text-zinc-300 leading-snug">{evt.headline}</p>

                  {/* DM-specific info */}
                  {evt.dm_advice && (
                    <p className="text-xs text-purple-400/70 mt-1 truncate">
                      DM: &quot;{evt.dm_advice}&quot;
                    </p>
                  )}
                </div>
              </div>
            </button>
          );
        })}

        {filteredTimeline.length === 0 && (
          <div className="p-8 text-center text-zinc-500 text-sm">
            {categoryFilter ? "No events match the selected filter" : "No critical events detected"}
          </div>
        )}
      </div>
    </div>
  );
}
