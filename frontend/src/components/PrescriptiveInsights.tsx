"use client";

import { useEffect, useState } from "react";
import { fetchRecommendations } from "@/lib/api";
import type { Recommendation } from "@/lib/api";

interface Props {
  runId: string;
}

const CAT_COLORS: Record<string, string> = {
  prompt_engineering: "border-amber-500/30 bg-amber-500/5",
  tooling: "border-blue-500/30 bg-blue-500/5",
  architecture: "border-purple-500/30 bg-purple-500/5",
  dm_config: "border-purple-500/30 bg-purple-500/5",
  exploration: "border-emerald-500/30 bg-emerald-500/5",
  efficiency: "border-emerald-500/30 bg-emerald-500/5",
};

const CAT_LABELS: Record<string, string> = {
  prompt_engineering: "Prompt Engineering",
  tooling: "Tooling",
  architecture: "Architecture",
  dm_config: "DM Configuration",
  exploration: "Exploration Strategy",
  efficiency: "Efficiency",
};

export function PrescriptiveInsights({ runId }: Props) {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchRecommendations(runId)
      .then((r) => { setRecs(r); setLoading(false); })
      .catch(() => setLoading(false));
  }, [runId]);

  if (loading) {
    return (
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-5 mt-6">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-sm">🤖</span>
          <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide">
            Generating Insights…
          </h3>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-slate-700/30 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (recs.length === 0) return null;

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-5 mt-6">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm">🤖</span>
        <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide">
          What Should Change Next?
        </h3>
      </div>
      <p className="text-xs text-zinc-500 mb-4">
        Automated prescriptive insights generated from run analysis
      </p>

      <div className="space-y-3">
        {recs.map((rec, i) => (
          <div
            key={i}
            className={`border rounded-lg p-4 transition-colors duration-300 ${
              CAT_COLORS[rec.category] ?? "border-zinc-700/50 bg-zinc-800/30"
            }`}
          >
            <div className="flex items-start gap-3">
              <span className="text-base flex-shrink-0 mt-0.5">{rec.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-zinc-200">{rec.title}</span>
                  <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-medium px-1.5 py-0.5 bg-zinc-800/50 rounded">
                    {CAT_LABELS[rec.category] ?? rec.category}
                  </span>
                </div>
                <p className="text-xs text-zinc-400 leading-relaxed">{rec.detail}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
