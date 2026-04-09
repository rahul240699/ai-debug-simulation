/** API fetch wrappers for the backend legibility endpoints. */

import type { RunDiagnosis, BeliefComparison } from "./types";

const BASE = "/api";

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
