/** API fetch wrappers for the backend legibility endpoints. */

const BASE = "/api";

export async function fetchRuns() {
  const res = await fetch(`${BASE}/runs`);
  return res.json();
}

export async function fetchRun(id: string) {
  const res = await fetch(`${BASE}/runs/${id}`);
  return res.json();
}

export async function fetchEvents(runId: string) {
  const res = await fetch(`${BASE}/runs/${runId}/events`);
  return res.json();
}

export async function fetchGridAtTurn(runId: string, turn: number) {
  const res = await fetch(`${BASE}/runs/${runId}/grid/${turn}`);
  return res.json();
}

export async function fetchBeliefs(runId: string, agentId: string, turn: number) {
  const res = await fetch(`${BASE}/runs/${runId}/beliefs/${agentId}/${turn}`);
  return res.json();
}

export async function fetchDiagnosis(runId: string) {
  const res = await fetch(`${BASE}/runs/${runId}/diagnosis`);
  return res.json();
}
