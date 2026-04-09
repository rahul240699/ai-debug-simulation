/** TypeScript equivalents of backend schemas. */

// ── Core types ──────────────────────────────────────────────────────────────

export interface MetricsCard {
  avg_information_lag: number;
  discrepancy_count: number;
  coordination_efficiency: number | null;
}

export interface CriticalEvent {
  turn_number: number;
  agent_id: string;
  event_type: "decision_point" | "critical_divergence" | "dm_oracle" | "coordination";
  severity: "green" | "yellow" | "red";
  headline: string;
  details: string | null;
  dm_query: string | null;
  dm_advice: string | null;
  stale_turns: number | null;
}

export interface FailureCategory {
  category: string;
  count: number;
  description: string;
  related_turns: number[];
}

export interface DiagnosisSummary {
  root_cause: string;
  failure_categories: FailureCategory[];
}

export interface EventRecord {
  run_id: string;
  turn_number: number;
  agent_id: string;
  timestamp: string;
  observed_state: {
    agent_position: number[];
    current_cell: string;
    adjacent_cells: Record<string, string>;
    visible_entities: Array<{ type: string; id: string; position: number[] }>;
    turn_number: number;
    has_key: boolean;
    messages_received: Array<{ from: string; text: string; sent_turn: number }>;
  };
  belief_before: {
    grid_knowledge: Record<string, string>;
    key_location: number[] | null;
    exit_location: number[] | null;
    door_location: number[] | null;
    partner_location: number[] | null;
    has_key: boolean;
    partner_has_key: boolean;
    last_updated_turn: number;
  };
  belief_after: {
    grid_knowledge: Record<string, string>;
    key_location: number[] | null;
    exit_location: number[] | null;
    door_location: number[] | null;
    partner_location: number[] | null;
    has_key: boolean;
    partner_has_key: boolean;
    last_updated_turn: number;
  };
  rationale: string;
  chosen_action: string;
  action_args: Record<string, unknown>;
  action_result: {
    success: boolean;
    action: string;
    new_position: number[];
    message: string;
    game_over: boolean;
    win: boolean;
    advice?: string;
    stale_turns_count?: number;
  };
  discrepancy_detected: boolean;
  discrepancy_details: string | null;
  belief_diff: Array<Record<string, unknown>> | null;
  message_correlation_ids: string[];
  dm_query: string | null;
  dm_advice: string | null;
  dm_stale_turns_count: number | null;
}

export interface BeliefComparison {
  turn_number: number;
  agent_id: string;
  agent_position: number[];
  believed_grid: Record<string, string>;
  believed_key_location: number[] | null;
  believed_partner_location: number[] | null;
  believed_has_key: boolean;
  believed_partner_has_key: boolean;
  actual_adjacent: Record<string, string>;
  actual_key_exists: boolean;
  actual_visible_entities: Array<{ type: string; id: string; position: number[] }>;
  actual_has_key: boolean;
  chosen_action: string;
  action_args: Record<string, unknown>;
  action_result: Record<string, unknown>;
  discrepancy_detected: boolean;
  discrepancy_details: string | null;
  belief_diff: Array<Record<string, unknown>> | null;
}

export interface RunDiagnosis {
  run_id: string;
  seed: number | null;
  grid_size: string;
  dm_stale_turns: number;
  total_turns: number;
  game_over: boolean;
  win: boolean;
  metrics: MetricsCard;
  summary: DiagnosisSummary;
  timeline: CriticalEvent[];
  events: EventRecord[];
}

