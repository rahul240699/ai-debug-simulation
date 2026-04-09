/** TypeScript equivalents of backend schemas. */

export interface Position {
  row: number;
  col: number;
}

export interface ObservedState {
  agent_position: Position;
  adjacent_cells: Record<string, string>;
  visible_entities: Array<{ type: string; id: string; position: Position }>;
  turn_number: number;
  has_key: boolean;
}

export interface AgentBeliefModel {
  grid_knowledge: Record<string, string | null>;
  key_location: Position | null;
  exit_location: Position | null;
  partner_location: Position | null;
  has_key: boolean;
  partner_has_key: boolean;
  last_updated_turn: number;
}

export interface ActionResult {
  success: boolean;
  action: string;
  new_position: Position;
  message: string;
  game_over: boolean;
  win: boolean;
}

export interface EventRecord {
  run_id: string;
  turn_number: number;
  agent_id: string;
  timestamp: string;
  observed_state: ObservedState;
  internal_belief_model: AgentBeliefModel;
  rationale: string;
  chosen_action: string;
  action_result: ActionResult;
  discrepancy_detected: boolean;
  discrepancy_details: string | null;
  belief_diff: Record<string, unknown>[] | null;
}

export interface RunSummary {
  run_id: string;
  started_at: string;
  outcome: "win" | "loss" | "in_progress";
  total_turns: number;
  discrepancy_count: number;
}

export interface DiagnosisItem {
  category: "prompt" | "tool" | "coordination" | "stale_info";
  description: string;
  related_turns: number[];
  severity: "low" | "medium" | "high";
}
