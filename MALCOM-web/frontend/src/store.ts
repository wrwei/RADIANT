import { reactive } from "vue";
import type {
  CaseStudy,
  ChatMessage,
  ClientMessage,
  GradleCommand,
  HistoryEntry,
  ModelInfo,
  PhaseStatus,
  PipelinePhase,
  RequirementFile,
  ServerMessage,
  ThreadState,
  VerificationInfo,
} from "./types";

// ---------------------------------------------------------------------------
// Reactive application state (module-level singleton — one UI per page).
// ---------------------------------------------------------------------------
interface State {
  connected: boolean;
  agents: Record<string, string[]>;
  requiredAgents: Record<string, string[]>;
  pipeline: PipelinePhase[];
  requirements: RequirementFile[];
  caseStudies: CaseStudy[];
  selectedCaseStudy: string;
  selectedRequirement: string;
  // LLM model + agent-mode configuration (applies to subsequent runs).
  models: ModelInfo[];
  selectedModel: string;
  agentMode: string;
  configOpen: boolean;
  gradleCommands: Record<string, GradleCommand>;
  existingOutputs: string[];
  phaseStatuses: Record<string, PhaseStatus>;
  // Per-phase verification result + the phase's dedicated repair agent.
  verifications: Record<string, VerificationInfo>;
  repairAgents: Record<string, string>;

  // Per-task agent enable flags: agentEnabled[task][agent] = boolean
  agentEnabled: Record<string, Record<string, boolean>>;

  messages: ChatMessage[];
  working: { active: boolean; agent: string; startTime: number };
  progress: { active: boolean; phase: string; current: number; total: number; agent: string };
  // Per-task requirement feeding mode (defaults to "sequential" when unset).
  feedMode: Record<string, string>;
  // Fold-all broadcast: bump `signal` to push `collapsed` onto every message.
  fold: { signal: number; collapsed: boolean };
  inputCue: string | null;

  selectedTask: string | null;
  fileList: string[];
  fileTask: string;
  preview: { path: string; content: string } | null;

  // Digital Thread (traceability loom) overlay.
  thread: ThreadState;
}

export const state = reactive<State>({
  connected: false,
  agents: {},
  requiredAgents: {},
  pipeline: [],
  requirements: [],
  caseStudies: [],
  selectedCaseStudy: "",
  selectedRequirement: "",
  models: [],
  selectedModel: "",
  agentMode: "multi",
  configOpen: false,
  gradleCommands: {},
  existingOutputs: [],
  phaseStatuses: {},
  verifications: {},
  repairAgents: {},
  agentEnabled: {},
  messages: [],
  working: { active: false, agent: "", startTime: 0 },
  progress: { active: false, phase: "", current: 0, total: 0, agent: "" },
  feedMode: {},
  fold: { signal: 0, collapsed: false },
  inputCue: null,
  selectedTask: null,
  fileList: [],
  fileTask: "",
  preview: null,
  thread: { open: false, loading: false, data: null, error: "" },
});

// The active socket sender, injected by useSocket().
let sender: ((msg: ClientMessage) => void) | null = null;
export function bindSender(fn: (msg: ClientMessage) => void): void {
  sender = fn;
}
function send(msg: ClientMessage): void {
  sender?.(msg);
}

// Streaming bookkeeping: the in-progress agent message, if any.
let streaming: ChatMessage | null = null;

function finalizeStream(): void {
  if (streaming) streaming.streaming = false;
  streaming = null;
}

// ---------------------------------------------------------------------------
// Agent toggles
// ---------------------------------------------------------------------------
function initAgentToggles(): void {
  const map: Record<string, Record<string, boolean>> = {};
  for (const [task, agents] of Object.entries(state.agents)) {
    map[task] = {};
    for (const a of agents) map[task][a] = true;
  }
  state.agentEnabled = map;
}

export function isRequired(task: string, agent: string): boolean {
  return (state.requiredAgents[task] || []).includes(agent);
}

export function toggleAgent(task: string, agent: string): void {
  if (isRequired(task, agent)) return; // required agents stay on
  const t = state.agentEnabled[task];
  if (t) t[agent] = !t[agent];
}

// ---------------------------------------------------------------------------
// Inbound message handling
// ---------------------------------------------------------------------------
export function handleMessage(msg: ServerMessage): void {
  switch (msg.type) {
    case "connected": {
      state.agents = msg.agents || {};
      state.requiredAgents = msg.required_agents || {};
      state.pipeline = msg.pipeline || [];
      state.requirements = msg.requirements || [];
      state.caseStudies = msg.case_studies || [];
      state.selectedCaseStudy = msg.selected_case_study || "";
      state.selectedRequirement = msg.selected_requirement || "";
      state.gradleCommands = msg.gradle_commands || {};
      state.existingOutputs = msg.existing_outputs || [];
      state.phaseStatuses = msg.phase_statuses || {};
      state.verifications = msg.verifications || {};
      state.repairAgents = msg.repair_agents || {};
      if (msg.models_config) {
        state.models = msg.models_config.models || [];
        state.selectedModel = msg.models_config.selected || "";
        state.agentMode = msg.models_config.agent_mode || "multi";
      }
      initAgentToggles();
      replayHistory(msg.history || []);
      break;
    }
    case "agent_message":
      finalizeStream();
      state.messages.push({ kind: "agent", agent: msg.agent, content: msg.content });
      break;
    case "agent_stream": {
      if (!streaming || streaming.agent !== msg.agent) {
        finalizeStream();
        streaming = { kind: "agent", agent: msg.agent, content: msg.content, streaming: true };
        state.messages.push(streaming);
      } else {
        streaming.content += "\n" + msg.content;
      }
      break;
    }
    case "agent_working":
      state.working = { active: true, agent: msg.agent, startTime: Date.now() };
      break;
    case "verification":
      state.verifications[msg.phase] = { passed: msg.passed, checks: msg.checks };
      break;
    case "progress":
      state.progress = {
        active: true,
        phase: msg.phase,
        current: msg.current,
        total: msg.total,
        agent: msg.agent,
      };
      // Reset the elapsed timer per agent so "working… Ns" tracks the current call.
      state.working = { active: true, agent: msg.agent, startTime: Date.now() };
      break;
    case "input_request":
      state.inputCue = msg.prompt || "Agent is waiting for input…";
      break;
    case "phase_complete":
      finalizeStream();
      state.working.active = false;
      state.progress.active = false;
      state.phaseStatuses[msg.phase] = msg.status || "completed";
      state.messages.push({
        kind: "system",
        content: `Stage "${msg.phase}" ${msg.status || "completed"}.`,
      });
      if (state.selectedTask === msg.phase) listFiles(msg.phase);
      void refreshExistingOutputs();
      if (state.thread.open && (msg.phase === "ciaReport" || msg.phase === "ciaSnapshot")) {
        void fetchThread();
      }
      break;
    case "error":
      state.messages.push({ kind: "system", content: msg.message, isError: true });
      state.working.active = false;
      state.progress.active = false;
      break;
    case "file_list":
      state.fileTask = msg.task;
      state.fileList = (msg.files || []).map((f) => (typeof f === "string" ? f : f.path));
      break;
    case "clear_result":
      if (msg.status === "ok") {
        state.messages.push({ kind: "system", content: `Cleared ${msg.count} file(s).` });
        if (state.selectedTask) listFiles(state.selectedTask);
      } else {
        state.messages.push({ kind: "system", content: `Clear failed: ${msg.message}`, isError: true });
      }
      break;
    case "case_study_changed":
      state.requirements = msg.requirements || [];
      // Drop everything tied to the previous study.
      state.selectedRequirement = "";
      state.preview = null;
      state.fileList = [];
      state.fileTask = "";
      state.selectedTask = null;
      state.existingOutputs = msg.existing_outputs || [];
      state.phaseStatuses = msg.phase_statuses || {};
      state.verifications = {};
      state.messages.push({ kind: "system", content: "Switched case study. Requirements updated." });
      break;
    case "config_changed":
      state.selectedModel = msg.selected_model || state.selectedModel;
      state.agentMode = msg.agent_mode || state.agentMode;
      break;
  }
}

function replayHistory(history: HistoryEntry[]): void {
  for (const m of history) {
    if (m.type === "agent_message") {
      state.messages.push({ kind: "agent", agent: m.agent, content: m.content });
    } else if (m.type === "system") {
      state.messages.push({ kind: "system", content: m.content });
    }
  }
}

export function setConnected(v: boolean): void {
  state.connected = v;
  if (!v) state.working.active = false;
}

// ---------------------------------------------------------------------------
// Actions (client -> server)
// ---------------------------------------------------------------------------
export function selectCaseStudy(configPath: string): void {
  state.selectedCaseStudy = configPath;
  send({ type: "select_case_study", config_path: configPath });
}

// ---- Run configuration (LLM model + agent mode) ----
export function openConfig(): void {
  state.configOpen = true;
  void fetchModels(); // refresh in case the connect payload predates this server
}
export function closeConfig(): void {
  state.configOpen = false;
}
export function setRunConfig(model: string, agentMode: string): void {
  state.selectedModel = model;
  state.agentMode = agentMode;
  send({ type: "set_config", model, agent_mode: agentMode });
}
export async function fetchModels(): Promise<void> {
  try {
    const resp = await fetch("/api/models");
    if (!resp.ok) return;
    const data = await resp.json();
    state.models = data.models || [];
    if (data.selected) state.selectedModel = data.selected;
    if (data.agent_mode) state.agentMode = data.agent_mode;
  } catch {
    /* ignore — keep whatever the connect payload provided */
  }
}

export function selectRequirement(path: string): void {
  state.selectedRequirement = path;
  send({ type: "select_requirement", path });
  void previewRequirement(path);
}

async function loadPreview(url: string, path: string): Promise<void> {
  try {
    const resp = await fetch(url);
    const data = await resp.json();
    state.preview = { path, content: data.error ? `Error: ${data.error}` : data.content };
  } catch (err) {
    state.preview = { path, content: `Failed to load: ${err}` };
  }
}

export function previewFile(path: string): Promise<void> {
  return loadPreview(`/api/files/${encodeURIComponent(path)}`, path);
}

export function previewRequirement(path: string): Promise<void> {
  return loadPreview(`/api/req-files/${encodeURIComponent(path)}`, path);
}

export function selectTask(task: string): void {
  state.selectedTask = task;
  send({ type: "list_files", task });
}

export function feedMode(task: string): string {
  return state.feedMode[task] || "batch";
}

export function setFeedMode(task: string, mode: string): void {
  state.feedMode[task] = mode;
}

export function startTask(task: string): void {
  const agents = state.agents[task] || [];
  const disabled = agents.filter((a) => state.agentEnabled[task]?.[a] === false);
  const requirements = task === "behaviour" ? "" : state.selectedRequirement;
  state.progress = { active: false, phase: "", current: 0, total: 0, agent: "" };
  send({
    type: "start_phase",
    phase: task,
    requirements,
    disabled_agents: disabled,
    feed_mode: feedMode(task),
  });
  state.phaseStatuses[task] = "running";
}

export function stopPhase(): void {
  send({ type: "stop_phase" });
}

export function foldAll(collapsed: boolean): void {
  state.fold = { signal: state.fold.signal + 1, collapsed };
}

export function clearDialogue(): void {
  finalizeStream();
  state.messages = [];
  state.working.active = false;
  state.progress.active = false;
  state.inputCue = null;
  send({ type: "clear_dialogue" }); // also clear the persisted server-side log
}

export function startCommand(cmdId: string): void {
  send({ type: "start_command", command: cmdId });
  state.phaseStatuses[cmdId] = "running";
}

// ---------------------------------------------------------------------------
// Digital Thread (traceability loom)
// ---------------------------------------------------------------------------
export async function fetchThread(): Promise<void> {
  state.thread.loading = true;
  state.thread.error = "";
  try {
    const resp = await fetch("/api/thread");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    state.thread.data = await resp.json();
  } catch (e) {
    state.thread.error = String(e);
  } finally {
    state.thread.loading = false;
  }
}

export function openThread(): void {
  state.thread.open = true;
  void fetchThread();
}

export function closeThread(): void {
  state.thread.open = false;
}

export function submitInput(text: string): void {
  const trimmed = text.trim();
  if (!trimmed) return;
  if (state.inputCue) {
    send({ type: "user_input", content: trimmed });
    state.inputCue = null;
  } else if (state.selectedTask) {
    send({ type: "refine", phase: state.selectedTask, message: trimmed });
  }
}

export function listFiles(task: string): void {
  send({ type: "list_files", task });
}

export function clearOutput(task: string): void {
  send({ type: "clear_output", task });
}

// ---------------------------------------------------------------------------
// Derived helpers
// ---------------------------------------------------------------------------
export function phaseStatus(phase: PipelinePhase): PhaseStatus {
  if (phase.tasks && phase.tasks.length > 0) {
    return state.phaseStatuses[phase.tasks[0]] || "idle";
  }
  return "idle";
}

// Pipeline order for the verification gate (matches web/bridge.py STAGE_NAMES).
const PHASE_ORDER = ["concept", "dsml", "model", "behaviour"];

// A task's Start is gate-locked when its immediate predecessor failed
// verification (status "failed"). Returns the blocking predecessor, or null.
export function gateBlocker(task: string): string | null {
  const i = PHASE_ORDER.indexOf(task);
  if (i <= 0) return null;
  const pred = PHASE_ORDER[i - 1];
  // Backend sends "failed" (and "error"); PhaseStatus type doesn't list "failed".
  const s = state.phaseStatuses[pred] as string | undefined;
  return s === "error" || s === "failed" ? pred : null;
}

export function verificationOf(task: string): VerificationInfo | null {
  return state.verifications[task] || null;
}

export function repairAgentOf(task: string): string {
  return state.repairAgents[task] || "";
}

export function runningStage(): string | null {
  for (const [k, v] of Object.entries(state.phaseStatuses)) {
    if (v === "running") return k;
  }
  return null;
}

export function gradleDepMissing(cmdId: string): string | null {
  const needs = state.gradleCommands[cmdId]?.needs;
  if (needs && !state.existingOutputs.includes(needs)) return needs;
  return null;
}

// Refetch the output file list so gradle dependency gates update after a run.
export async function refreshExistingOutputs(): Promise<void> {
  try {
    const resp = await fetch("/api/files");
    const data = await resp.json();
    state.existingOutputs = (data.files || []).map((f: string | { path: string }) =>
      typeof f === "string" ? f : f.path,
    );
  } catch {
    /* ignore */
  }
}
