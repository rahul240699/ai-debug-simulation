"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { fetchDiagnosis, startSimulation, pollSimulationStatus } from "@/lib/api";
import type { SimulationConfig, SimulationStatus } from "@/lib/api";
import type { RunDiagnosis, CriticalEvent, EventRecord } from "@/lib/types";
import { MetricsCards } from "@/components/MetricsCards";
import { SummaryBanner } from "@/components/SummaryBanner";
import { DivergenceTimeline } from "@/components/DivergenceTimeline";
import { WhyInspector } from "@/components/WhyInspector";
import { SimulationControls } from "@/components/SimulationControls";
import { StepViewer } from "@/components/StepViewer";

type ViewMode = "diagnosis" | "steps";

const POLL_INTERVAL_MS = 3000;

export default function DashboardPage() {
  const [data, setData] = useState<RunDiagnosis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<CriticalEvent | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("diagnosis");
  const [simStatus, setSimStatus] = useState<SimulationStatus | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  // Load the sample run on first load
  useEffect(() => {
    fetchDiagnosis("latest")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const handleStart = useCallback(async (config: SimulationConfig) => {
    // Reset state
    stopPolling();
    setIsRunning(true);
    setError(null);
    setData(null);
    setSelectedEvent(null);
    setSimStatus(null);

    try {
      // Fire — returns immediately with session_id
      const startResult = await startSimulation(config);

      setSimStatus({
        session_id: startResult.session_id,
        status: "running",
        run_id: startResult.run_id,
        current_turn: 0,
        max_turns: startResult.max_turns,
        grid_size: startResult.grid_size,
      });

      // Poll for progress
      pollRef.current = setInterval(async () => {
        try {
          const status = await pollSimulationStatus(startResult.session_id);
          setSimStatus(status);

          if (status.status === "completed") {
            stopPolling();
            // Fetch full diagnosis for the completed run
            const diagnosis = await fetchDiagnosis(status.run_id);
            setData(diagnosis);
            setIsRunning(false);
            setViewMode("diagnosis");
          } else if (status.status === "failed") {
            stopPolling();
            setError(status.error ?? "Simulation failed");
            setIsRunning(false);
          }
        } catch (pollErr) {
          // Don't stop polling on transient network errors
          console.warn("Poll error:", pollErr);
        }
      }, POLL_INTERVAL_MS);

    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start simulation");
      setIsRunning(false);
    }
  }, [stopPolling]);

  // ── Running state: show progress ──────────────────────────────────────
  if (isRunning && simStatus) {
    const pct = simStatus.max_turns > 0
      ? Math.round((simStatus.current_turn / simStatus.max_turns) * 100)
      : 0;

    return (
      <main className="max-w-7xl mx-auto px-6 py-8">
        <SimulationControls onStart={handleStart} isRunning={isRunning} />
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-8 max-w-md w-full text-center">
            <div className="w-8 h-8 border-2 border-zinc-600 border-t-emerald-400 rounded-full animate-spin mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-zinc-200 mb-2">Simulation in Progress…</h2>
            <p className="text-sm text-zinc-400 mb-4">
              {simStatus.grid_size} grid · {simStatus.max_turns / 2} turns × 2 agents = {simStatus.max_turns} steps
            </p>
            {/* Turn counter */}
            <div className="mb-3">
              <span className="text-3xl font-bold text-emerald-400 tabular-nums">
                {simStatus.current_turn}
              </span>
              <span className="text-zinc-500 text-lg"> / {simStatus.max_turns} steps</span>
            </div>
            {/* Progress bar */}
            <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 transition-all duration-500 ease-out"
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="text-xs text-zinc-600 mt-3">
              Polling every {POLL_INTERVAL_MS / 1000}s · Session {simStatus.session_id}
            </p>
          </div>
        </div>
      </main>
    );
  }

  if (error && !data) {
    return (
      <main className="max-w-7xl mx-auto px-6 py-8">
        <SimulationControls onStart={handleStart} isRunning={isRunning} />
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="bg-zinc-900 border border-red-500/30 rounded-lg p-8 max-w-md">
            <h2 className="text-red-400 text-lg font-semibold mb-2">Error</h2>
            <p className="text-zinc-400 text-sm">{error}</p>
            <p className="text-zinc-500 text-xs mt-4">
              Make sure the backend is running: <code className="text-zinc-300">uvicorn src.main:app --reload</code>
            </p>
          </div>
        </div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="max-w-7xl mx-auto px-6 py-8">
        <SimulationControls onStart={handleStart} isRunning={isRunning} />
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="flex items-center gap-3 text-zinc-400">
            <div className="w-4 h-4 border-2 border-zinc-600 border-t-zinc-300 rounded-full animate-spin" />
            Loading diagnosis data…
          </div>
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
      {/* Simulation Controls */}
      <SimulationControls onStart={handleStart} isRunning={isRunning} />

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Diagnosis Dashboard</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Run <code className="text-zinc-400">{data.run_id}</code> · {data.grid_size} grid · {data.total_turns} turns · DM stale: {data.dm_stale_turns}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* View mode toggle */}
          <div className="flex bg-zinc-800 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode("diagnosis")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                viewMode === "diagnosis"
                  ? "bg-zinc-700 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Diagnosis
            </button>
            <button
              onClick={() => setViewMode("steps")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                viewMode === "steps"
                  ? "bg-zinc-700 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Step-by-Step
            </button>
          </div>
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${
            data.win
              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
              : "bg-red-500/10 text-red-400 border border-red-500/20"
          }`}>
            {data.win ? "WIN" : "LOSS"}
          </div>
        </div>
      </div>

      {viewMode === "diagnosis" ? (
        <>
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
        </>
      ) : (
        /* Step-by-Step Viewer */
        <StepViewer events={data.events} />
      )}
    </main>
  );
}
