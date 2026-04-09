/** Divergence Timeline — vertical timeline showing only critical events. */

import type { CriticalEvent } from "@/lib/types";

interface Props {
  timeline: CriticalEvent[];
  selectedEvent: CriticalEvent | null;
  onSelectEvent: (event: CriticalEvent) => void;
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
    dot: "bg-red-400",
    border: "border-red-500/20 hover:border-red-500/40",
    bg: "bg-red-500/5",
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

export function DivergenceTimeline({ timeline, selectedEvent, onSelectEvent }: Props) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg">
      <div className="px-4 py-3 border-b border-zinc-800">
        <h3 className="text-sm font-semibold text-zinc-300">Divergence Timeline</h3>
        <p className="text-xs text-zinc-500 mt-0.5">
          {timeline.length} critical events · Click to inspect
        </p>
      </div>
      <div className="max-h-[600px] overflow-y-auto">
        {timeline.map((evt, i) => {
          const styles = SEVERITY_STYLES[evt.severity] ?? SEVERITY_STYLES.yellow;
          const isSelected =
            selectedEvent?.turn_number === evt.turn_number &&
            selectedEvent?.agent_id === evt.agent_id;

          return (
            <button
              key={`${evt.turn_number}-${evt.agent_id}-${i}`}
              onClick={() => onSelectEvent(evt)}
              className={`w-full text-left px-4 py-3 border-b border-zinc-800/50 transition-colors cursor-pointer ${
                isSelected ? `${styles.bg} border-l-2 ${styles.border}` : "hover:bg-zinc-800/50"
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Timeline dot */}
                <div className="flex flex-col items-center pt-1">
                  <div className={`w-2.5 h-2.5 rounded-full ${styles.dot}`} />
                  {i < timeline.length - 1 && (
                    <div className="w-px h-full bg-zinc-800 mt-1" />
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

        {timeline.length === 0 && (
          <div className="p-8 text-center text-zinc-500 text-sm">
            No critical events detected
          </div>
        )}
      </div>
    </div>
  );
}
