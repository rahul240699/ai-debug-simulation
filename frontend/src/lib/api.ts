/** API fetch wrappers for the backend legibility endpoints. */

import type { RunDiagnosis, BeliefComparison } from "./types";

const BASE = "/api";
const BACKEND = "http://localhost:8000/api";

export interface SimulationConfig {
  seed?: number | null;
  max_turns: number;
  width: number;
  height: number;
  wall_density: number;
  dm_stale_turns: number;
}

export interface SimulationStartResult {
  session_id: string;
  run_id: string;
  status: "running";
  grid_size: string;
  max_turns: number;
}

export interface SimulationStatus {
  session_id: string;
  status: "running" | "completed" | "failed";
  run_id: string;
  current_turn: number;
  max_turns: number;
  grid_size: string;
  error?: string;
}

export async function startSimulation(config: SimulationConfig): Promise<SimulationStartResult> {
  const res = await fetch(`${BACKEND}/simulation/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Simulation failed: ${res.status} — ${text}`);
  }
  return res.json();
}

export async function pollSimulationStatus(sessionId: string): Promise<SimulationStatus> {
  const res = await fetch(`${BACKEND}/simulation/status/${encodeURIComponent(sessionId)}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Status poll failed: ${res.status} — ${text}`);
  }
  return res.json();
}

export async function fetchDiagnosis(runId: string = "latest"): Promise<RunDiagnosis> {
  const res = await fetch(`${BASE}/diagnose?run_id=${encodeURIComponent(runId)}`);
  if (!res.ok) throw new Error(`Failed to fetch diagnosis: ${res.status}`);
  return res.json();
}

export async function fetchEventDetail(runId: string, turn: number): Promise<BeliefComparison> {
  const res = await fetch(`${BASE}/runs/${encodeURIComponent(runId)}/events/${turn}`);
  if (!res.ok) throw new Error(`Failed to fetch event detail: ${res.status}`);
  return res.json();
}

export async function fetchRuns(): Promise<Array<{ run_id: string; total_turns: number; win: boolean }>> {
  const res = await fetch(`${BASE}/runs`);
  if (!res.ok) throw new Error(`Failed to fetch runs: ${res.status}`);
  return res.json();
}
