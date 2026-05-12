/** Core metrics cards — Info Lag, Discrepancy Count, Coordination Efficiency. */

import type { MetricsCard } from "@/lib/types";

interface Props {
  metrics: MetricsCard;
}

export function MetricsCards({ metrics }: Props) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <MetricCard
        label="Avg Information Lag"
        value={`${metrics.avg_information_lag} turns`}
        description="How many turns behind agents were on average"
        color="amber"
      />
      <MetricCard
        label="Discrepancy Count"
        value={String(metrics.discrepancy_count)}
        description="Times an agent hit a wall or failed an interaction"
        color="red"
      />
      <MetricCard
        label="Coordination Efficiency"
        value={
          metrics.coordination_efficiency !== null
            ? `${metrics.coordination_efficiency} turns`
            : "N/A"
        }
        description="Turns to share the 'Key Found' message"
        color="blue"
      />
    </div>
  );
}

function MetricCard({
  label,
  value,
  description,
  color,
}: {
  label: string;
  value: string;
  description: string;
  color: "amber" | "red" | "blue";
}) {
  const borderColor = {
    amber: "border-amber-500/20",
    red: "border-red-500/20",
    blue: "border-blue-500/20",
  }[color];

  const valueColor = {
    amber: "text-amber-400",
    red: "text-red-400",
    blue: "text-blue-400",
  }[color];

  return (
    <div className={`bg-zinc-900 border ${borderColor} rounded-lg p-4`}>
      <p className="text-xs text-zinc-500 uppercase tracking-wide font-medium">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${valueColor}`}>{value}</p>
      <p className="text-xs text-zinc-600 mt-1">{description}</p>
    </div>
  );
}
