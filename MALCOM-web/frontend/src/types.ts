// Wire protocol shared with web/server.py. Kept byte-for-byte compatible with
// the existing FastAPI WebSocket + REST contract.

export type PhaseStatus = "idle" | "running" | "completed" | "error";

export interface CaseStudy {
  name: string;
  config_path: string;
}

export interface RequirementFile {
  path: string;
  name: string;
}

export interface ModelInfo {
  key: string;
  name: string;
}

export interface ModelsConfig {
  models: ModelInfo[];
  default: string;
  selected: string;
  agent_mode: string;
}

export type PhaseType = "manual" | "llm" | "gradle";

export interface PipelinePhase {
  id: string;
  label: string;
  type: PhaseType;
  tasks?: string[];
  commands?: string[];
}

export interface GradleCommand {
  label?: string;
  needs?: string | null;
}

export interface OutputFile {
  path: string;
  size?: number;
}

// ---- History entries (replayed on connect) ----
export interface HistoryAgentMessage {
  type: "agent_message";
  agent: string;
  content: string;
  phase?: string;
}
export interface HistorySystemMessage {
  type: "system";
  content: string;
}
export type HistoryEntry = HistoryAgentMessage | HistorySystemMessage;

// ---- Server -> client messages (discriminated union on `type`) ----
export interface ConnectedMsg {
  type: "connected";
  stages: string[];
  agents: Record<string, string[]>;
  required_agents: Record<string, string[]>;
  pipeline: PipelinePhase[];
  requirements: RequirementFile[];
  case_studies: CaseStudy[];
  selected_requirement: string;
  selected_case_study: string;
  history: HistoryEntry[];
  phase_statuses: Record<string, PhaseStatus>;
  verifications: Record<string, VerificationInfo>;
  repair_agents: Record<string, string>;
  gradle_commands: Record<string, GradleCommand>;
  models_config?: ModelsConfig;
  existing_outputs: string[];
}
export interface AgentMessageMsg {
  type: "agent_message";
  agent: string;
  content: string;
  phase?: string;
}
export interface AgentStreamMsg {
  type: "agent_stream";
  agent: string;
  content: string;
  phase?: string;
}
export interface AgentWorkingMsg {
  type: "agent_working";
  agent: string;
}
export interface InputRequestMsg {
  type: "input_request";
  prompt: string;
}
export interface PhaseCompleteMsg {
  type: "phase_complete";
  phase: string;
  status?: PhaseStatus;
}
export interface ProgressMsg {
  type: "progress";
  phase: string;
  current: number;
  total: number;
  agent: string;
}
export interface VerificationCheck {
  name: string;
  kind: string;
  ok: boolean;
  unverifiable: boolean;
  detail: string;
}
export interface VerificationInfo {
  passed: boolean;
  checks: VerificationCheck[];
}
export interface VerificationMsg {
  type: "verification";
  phase: string;
  passed: boolean;
  checks: VerificationCheck[];
}
export interface ErrorMsg {
  type: "error";
  message: string;
}
export interface FileListMsg {
  type: "file_list";
  task: string;
  files: (string | OutputFile)[];
}
export interface ClearResultMsg {
  type: "clear_result";
  status: "ok" | "error";
  count?: number;
  task?: string;
  message?: string;
}
export interface CaseStudyChangedMsg {
  type: "case_study_changed";
  config_path: string;
  requirements: RequirementFile[];
  existing_outputs?: string[];
  phase_statuses?: Record<string, PhaseStatus>;
}
export interface ConfigChangedMsg {
  type: "config_changed";
  selected_model: string;
  agent_mode: string;
}

export type ServerMessage =
  | ConnectedMsg
  | AgentMessageMsg
  | AgentStreamMsg
  | AgentWorkingMsg
  | InputRequestMsg
  | PhaseCompleteMsg
  | ProgressMsg
  | VerificationMsg
  | ErrorMsg
  | FileListMsg
  | ClearResultMsg
  | CaseStudyChangedMsg
  | ConfigChangedMsg;

// ---- Client -> server messages ----
export type ClientMessage =
  | { type: "select_requirement"; path: string }
  | { type: "select_case_study"; config_path: string }
  | { type: "start_phase"; phase: string; requirements: string; disabled_agents: string[]; feed_mode: string }
  | { type: "start_command"; command: string }
  | { type: "refine"; phase: string; message: string }
  | { type: "stop_phase" }
  | { type: "user_input"; content: string }
  | { type: "list_files"; task: string }
  | { type: "clear_output"; task: string }
  | { type: "set_config"; model: string; agent_mode: string }
  | { type: "clear_dialogue" };

// ---- Local view-model types ----
export interface ChatMessage {
  kind: "agent" | "system";
  agent?: string;
  content: string;
  isError?: boolean;
  streaming?: boolean;
}

export interface ThreadReqNode {
  id: string; cid: string; name: string; description: string;
  traced: boolean; impacted: boolean;
}
export interface ThreadElemNode {
  key: string; label: string; phase: string; impacted: boolean;
}
export interface ThreadLink {
  id: number; gid: string; from: string; phase: string; to: string;
  source: Record<string, unknown>; impacted: boolean;
}
export interface ThreadGraph {
  case_study: string;
  columns: string[];
  nodes: { requirement: ThreadReqNode[]; [phase: string]: (ThreadReqNode | ThreadElemNode)[] };
  links: ThreadLink[];
  impact: { requirements: string[]; elements: string[] };
  stats: { total_links: number; by_phase: Record<string, number>; coverage: Record<string, number> };
}
export interface ThreadState {
  open: boolean; loading: boolean; data: ThreadGraph | null; error: string;
}
