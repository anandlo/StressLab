export enum InputMode {
  TEXT = "text",
  KEYBOARD = "keyboard",
  SPACEBAR = "spacebar",
  CLICK = "click",
  NONE = "none",
}

export enum StimulusType {
  TEXT = "text",
  STROOP = "stroop",
  ARROWS = "arrows",
  SHAPE = "shape",
  SEQUENCE = "sequence",
  CARDS = "cards",
  GRID = "grid",
  TIMER_ONLY = "timer_only",
  LETTER_STREAM = "letter_stream",
  DUAL = "dual",
}

export enum Intensity {
  LOW = "low",
  MEDIUM = "medium",
  HIGH = "high",
}

export enum SessionState {
  IDLE = "idle",
  PRACTICE = "practice",
  RUNNING = "running",
  REST = "rest",
  PAUSED = "paused",
  COMPLETE = "complete",
}

export interface ParadigmMeta {
  id: string;
  label: string;
  reference: string;
  description: string;
  input_mode: InputMode;
  stimulus_type: StimulusType;
  base_time_sec: number;
  category: string;
}

export interface Trial {
  trial_id: string;
  paradigm_id: string;
  paradigm_label: string;
  difficulty: number;
  time_limit_sec: number;
  stimulus_type: StimulusType;
  input_mode: InputMode;
  stimulus: Record<string, unknown>;
  correct_answer: string;
  instruction: string;
  explanation?: string;
}

export interface TrialResult {
  trial_id: string;
  paradigm_id: string;
  paradigm_label: string;
  difficulty: number;
  time_limit_sec: number;
  correct_answer: string;
  user_response: string | null;
  is_correct: boolean;
  timed_out: boolean;
  response_time_ms: number;
  timestamp: string;
  elapsed_sec: number;
}

export type SoundType = "tick" | "beep" | "soft" | "none";

export interface SessionConfig {
  participant_id: string;
  duration_min: number;
  intensity: Intensity;
  paradigm_ids: string[];
  blocks: number;
  rest_duration_sec: number;
  practice_enabled: boolean;
  practice_trials_per_paradigm: number;
  sound_clicks_enabled: boolean;
  sound_countdown_enabled: boolean;
  sound_type: SoundType;
  session_name?: string;
  project_id?: string;
}

export interface SessionScore {
  correct: number;
  total: number;
  difficulty: number;
  block: number;
  total_blocks: number;
  elapsed_sec: number;
}

export interface PerParadigmStats {
  total: number;
  correct: number;
  accuracy_pct: number;
  avg_response_time_ms: number;
  metric_focus: "speed" | "accuracy" | "inhibition" | "mixed";
  // Speed-focused extras
  median_rt_ms?: number;
  lapse_rate?: number;
  // Inhibition-focused extras
  commission_errors?: number;
  timeout_rate?: number;
}

export interface SessionSummary {
  participant_id: string;
  session_start: string;
  session_end: string;
  duration_target_sec: number;
  intensity: string;
  paradigms_used: string[];
  total_tasks: number;
  correct_answers: number;
  accuracy_pct: number;
  max_difficulty: number;
  avg_response_time_ms: number;
  per_paradigm: Record<string, PerParadigmStats>;
  trials: TrialResult[];
}

export interface Participant {
  id: string;
  created: string;
  demographics: Record<string, string | number | null>;
  session_files: string[];
}

export interface ProtocolPreset {
  id: string;
  name: string;
  description: string;
  paradigm_ids: string[];
  duration_min: number;
  intensity: Intensity;
  blocks: number;
  rest_duration_sec: number;
}

export interface SessionListItem {
  filename: string;
  participant_id: string;
  session_start: string;
  total_tasks: number;
  accuracy_pct: number;
  intensity: string;
}

// WebSocket message types
export type WSOutgoingMessage =
  | { type: "start_session"; config: SessionConfig; auth_token?: string }
  | { type: "request_trial" }
  | { type: "submit_response"; trial_id: string; response: string; response_time_ms: number; timed_out: boolean }
  | { type: "rest_complete" }
  | { type: "stop_session" }
  | { type: "discard_session" };

export type WSIncomingMessage =
  | { type: "session_started"; score: SessionScore; guest?: boolean }
  | { type: "trial"; data: Trial }
  | { type: "result"; data: { correct: boolean; correct_answer: string; user_response: string; timed_out: boolean; response_time_ms: number; score: SessionScore; feedback: string | null } }
  | { type: "rest"; data: { duration_sec: number; block_completed: number; total_blocks: number } }
  | { type: "rest_ended"; score: SessionScore }
  | { type: "session_complete"; data: SessionSummary; session_file: string | null; guest?: boolean }
  | { type: "session_discarded" }
  | { type: "error"; message: string };

export interface User {
  id: string;
  email: string;
  phone: string | null;
  display_name: string | null;
  mfa_enabled: boolean;
  email_verified: boolean;
  created: string;
}

export interface Project {
  id: string;
  owner_id: string;
  name: string;
  description: string;
  created: string;
  session_files: string[];
}
