<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { state, runningStage, submitInput, clearDialogue, foldAll } from "../store";
import Panel from "./Panel.vue";
import AgentMessage from "./AgentMessage.vue";
import WorkingIndicator from "./WorkingIndicator.vue";

const scroller = ref<HTMLElement | null>(null);
const atBottom = ref(true);
const draft = ref("");

const breadcrumb = computed(() => {
  const r = runningStage();
  if (r) return `running · ${r}`;
  if (state.selectedTask) return `focus · ${state.selectedTask}`;
  return "idle";
});

const allFolded = ref(false);
function toggleFoldAll(): void {
  allFolded.value = !allFolded.value;
  foldAll(allFolded.value);
}

const placeholder = computed(() =>
  state.inputCue
    ? "Answer the agent's prompt…"
    : state.selectedTask
      ? `Refine “${state.selectedTask}” — type a message…`
      : "Select a stage to refine, or answer an agent prompt…",
);

function onScroll(): void {
  const el = scroller.value;
  if (!el) return;
  atBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
}

function scrollDown(): void {
  void nextTick(() => {
    const el = scroller.value;
    if (el && atBottom.value) el.scrollTop = el.scrollHeight;
  });
}

// Re-scroll on new messages and while streaming content grows.
watch(() => state.messages.length, scrollDown);
watch(
  () => state.messages[state.messages.length - 1]?.content,
  scrollDown,
);

function send(): void {
  if (!draft.value.trim()) return;
  submitInput(draft.value);
  draft.value = "";
}

function onKey(e: KeyboardEvent): void {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    send();
  }
}
</script>

<template>
  <Panel title="Dialogue">
    <template #actions>
      <span class="crumb">{{ breadcrumb }}</span>
      <button
        class="btn btn-sm clear-btn"
        :disabled="state.messages.length === 0"
        title="Collapse or expand every message"
        @click="toggleFoldAll()"
      >
        {{ allFolded ? "Unfold all" : "Fold all" }}
      </button>
      <button
        class="btn btn-sm clear-btn"
        :disabled="state.messages.length === 0"
        title="Clear the dialogue (also clears the saved log)"
        @click="clearDialogue()"
      >
        Clear
      </button>
    </template>

    <div class="dialogue">
      <div ref="scroller" class="messages" @scroll="onScroll">
        <p v-if="state.messages.length === 0" class="empty">
          No dialogue yet. Start a stage from the pipeline to watch the agents work.
        </p>
        <template v-for="(m, i) in state.messages" :key="i">
          <div v-if="m.kind === 'system'" class="system" :class="{ error: m.isError }">
            {{ m.content }}
          </div>
          <AgentMessage v-else :msg="m" />
        </template>
      </div>

      <WorkingIndicator />

      <div v-if="state.inputCue" class="cue">
        <span class="cue-icon">!</span>{{ state.inputCue }}
      </div>

      <div class="composer">
        <textarea
          v-model="draft"
          rows="3"
          :placeholder="placeholder"
          @keydown="onKey"
        />
        <button class="btn btn-primary send" @click="send">Send →</button>
      </div>
    </div>
  </Panel>
</template>

<style scoped>
.crumb {
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--text-muted);
}
.clear-btn {
  margin-left: 10px;
}
.clear-btn:disabled {
  opacity: 0.45;
  cursor: default;
}
.dialogue {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.messages {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  padding: 12px 16px;
}
.empty {
  color: var(--text-faint);
  font-size: 13px;
  text-align: center;
  margin-top: 36px;
}
.system {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  margin: 10px 0;
  padding: 5px 12px;
}
.system::before,
.system::after {
  content: "·";
  margin: 0 8px;
  color: var(--border-strong);
}
.system.error {
  color: var(--status-error);
}
.cue {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 16px 10px;
  padding: 8px 12px;
  font-size: 12.5px;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde8b5;
  border-radius: var(--radius-sm);
}
.cue-icon {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--status-running);
  color: #fff;
  font-weight: 700;
  font-size: 11px;
  display: grid;
  place-items: center;
}
.composer {
  flex: 0 0 auto;
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  background: var(--surface-2);
}
.composer textarea {
  flex: 1 1 auto;
  resize: none;
  font-family: inherit;
  font-size: 13px;
  color: var(--text);
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  padding: 9px 11px;
  line-height: 1.5;
}
.composer textarea:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-ring);
}
.send {
  height: 38px;
}
</style>
