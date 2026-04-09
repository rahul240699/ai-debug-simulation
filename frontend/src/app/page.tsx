"use client";

import { useEffect, useState } from "react";
import { fetchDiagnosis } from "@/lib/api";
import type { RunDiagnosis, CriticalEvent, EventRecord } from "@/lib/types";
import { MetricsCards } from "@/components/MetricsCards";
import { SummaryBanner } from "@/components/SummaryBanner";
import { DivergenceTimeline } from "@/components/DivergenceTimeline";
import { WhyInspector } from "@/components/WhyInspector";

export default function DashboardPage() {
  const [data, setData] = useState<RunDiagnosis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<CriticalEvent | null>(null);

  useEffect(() => {
    fetchDiagnosis("latest")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <main className="flex items-center justify-center min-h-screen">
        <div className="bg-zinc-900 border border-red-500/30 rounded-lg p-8 max-w-md">
          <h2 className="text-red-400 text-lg font-semibold mb-2">Connection Error</h2>
          <p className="text-zinc-400 text-sm">{error}</p>
          <p className="text-zinc-500 text-xs mt-4">
            Make sure the backend is running: <code className="text-zinc-300">uvicorn src.main:app --reload</code>
          </p>
        </div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="flex items-center justify-center min-h-screen">
        <div className="flex items-center gap-3 text-zinc-400">
          <div className="w-4 h-4 border-2 border-zinc-600 border-t-zinc-300 rounded-full animate-spin" />
          Loading diagnosis data…
        </div>
      </main>
    );
  }

  // Find the full EventRecord for the selected timeline event
  const selectedFullEvent: EventRecord | null = selectedEvent
    ? data.events.find(
        (e) =>
          e.turn_number === selectedEvent.turn_number &&
          e.agent_id === selectedEvent.agent_id
      ) ?? null
    : null;

  return (
    <main className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Diagnosis Dashboard</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Run <code className="text-zinc-400">{data.run_id}</code> · {data.grid_size} grid · {data.total_turns} turns · DM stale: {data.dm_stale_turns}
          </p>
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-medium ${
          data.win
            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
            : "bg-red-500/10 text-red-400 border border-red-500/20"
        }`}>
          {data.win ? "WIN" : "LOSS"}
        </div>
      </div>

      {/* Summary Banner */}
      <SummaryBanner summary={data.summary} win={data.win} />

      {/* Metrics */}
      <MetricsCards metrics={data.metrics} />

      {/* Main content: Timeline + Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mt-6">
        <div className="lg:col-span-2">
          <DivergenceTimeline
            timeline={data.timeline}
            selectedEvent={selectedEvent}
            onSelectEvent={setSelectedEvent}
          />
        </div>
        <div className="lg:col-span-3">
          <WhyInspector event={selectedFullEvent} timelineEvent={selectedEvent} />
        </div>
      </div>
    </main>
  );
}
