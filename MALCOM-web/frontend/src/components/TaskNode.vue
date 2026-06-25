<script setup lang="ts">
import { computed, ref } from "vue";
import {
  state, isRequired, toggleAgent, selectTask, startTask, stopPhase,
  feedMode, setFeedMode, gateBlocker, verificationOf, repairAgentOf,
} from "../store";

const props = defineProps<{ task: string }>();

const status = computed(() => state.phaseStatuses[props.task] || "idle");
const agents = computed(() => state.agents[props.task] || []);
const running = computed(() => status.value === "running");
const selected = computed(() => state.selectedTask === props.task);
// Behaviour always processes the whole document at once, so the toggle is N/A.
const showFeed = computed(() => props.task !== "behaviour");
// Verification gate: blocked when the predecessor phase failed verification.
const blocker = computed(() => gateBlocker(props.task));
// Latest verification result + the phase's dedicated repair agent.
const verification = computed(() => verificationOf(props.task));
const repairAgent = computed(() => repairAgentOf(props.task));
const checksOpen = ref(false);
</script>

<template>
  <div class="task" :class="{ selected }">
    <div class="task-head">
      <button class="task-name" @click="selectTask(task)" :title="`Show ${task} output files`">
        {{ task }}
      </button>
      <span class="status-dot" :class="status" />
      <button
        v-if="!running"
        class="btn btn-primary btn-sm"
        :disabled="!!blocker"
        :title="blocker ? `Blocked: phase '${blocker}' must pass verification first` : ''"
        @click="startTask(task)"
      >
        {{ blocker ? "Locked" : "Start" }}
      </button>
      <button v-else class="btn btn-sm stop" @click="stopPhase()">Stop</button>
    </div>

    <ul class="agents">
      <li v-for="a in agents" :key="a" class="agent" :class="{ locked: isRequired(task, a) }">
        <label>
          <input
            type="checkbox"
            :checked="state.agentEnabled[task]?.[a] !== false"
            :disabled="isRequired(task, a)"
            @change="toggleAgent(task, a)"
          />
          <span>{{ a }}</span>
        </label>
        <span v-if="isRequired(task, a)" class="req-tag">required</span>
      </li>
    </ul>

    <div v-if="verification" class="verify">
      <button class="verify-head" @click="checksOpen = !checksOpen">
        <span class="badge" :class="verification.passed ? 'pass' : 'fail'">
          {{ verification.passed ? "✓ verified" : "✗ failed" }}
        </span>
        <span class="verify-chev" :class="{ open: checksOpen }">▶</span>
      </button>
      <ul v-if="checksOpen" class="checks">
        <li v-for="c in verification.checks" :key="c.name" class="check">
          <span class="check-mark" :class="c.ok ? 'ok' : c.unverifiable ? 'warn' : 'bad'">
            {{ c.ok ? "OK" : c.unverifiable ? "warn" : "FAIL" }}
          </span>
          <span class="check-name">{{ c.name }}</span>
          <span v-if="c.detail" class="check-detail">{{ c.detail }}</span>
        </li>
      </ul>
    </div>

    <div v-if="repairAgent" class="repair-line" title="Side agent — runs only if verification fails">
      <span class="repair-tag">repair</span>
      <span class="repair-name">{{ repairAgent }}</span>
    </div>

    <div
      v-if="showFeed"
      class="feed-mode"
      title="sequential: one requirement at a time (clean per-requirement traceability). batch: all requirements in one pass (far fewer LLM calls, faster/cheaper)."
    >
      <span class="feed-label">feed</span>
      <button
        class="feed-btn"
        :class="{ on: feedMode(task) === 'sequential' }"
        :disabled="running"
        @click="setFeedMode(task, 'sequential')"
      >
        sequential
      </button>
      <button
        class="feed-btn"
        :class="{ on: feedMode(task) === 'batch' }"
        :disabled="running"
        @click="setFeedMode(task, 'batch')"
      >
        batch
      </button>
    </div>
  </div>
</template>

<style scoped>
.task {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  margin: 6px 0;
  background: var(--surface);
  overflow: hidden;
}
.task.selected {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-ring);
}
.task-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
}
.task-name {
  flex: 1 1 auto;
  text-align: left;
  background: transparent;
  border: none;
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
  padding: 0;
}
.task-name:hover {
  color: var(--accent);
}
.stop {
  color: var(--status-error);
  border-color: #f3c2c2;
  background: #fef2f2;
}
.stop:hover {
  background: #fde4e4;
}
.agents {
  list-style: none;
  margin: 0;
  padding: 6px 10px;
}
.agent {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 3px 0;
}
.agent label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
}
.agent.locked label {
  cursor: default;
}
.agent input {
  accent-color: var(--accent);
  width: 14px;
  height: 14px;
}
.req-tag {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-faint);
  background: var(--surface-hover);
  padding: 1px 6px;
  border-radius: var(--radius-pill);
}
.verify {
  border-top: 1px solid var(--border);
  padding: 6px 10px;
}
.verify-head {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
}
.badge {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-pill);
}
.badge.pass {
  color: #166534;
  background: #dcfce7;
}
.badge.fail {
  color: var(--status-error);
  background: #fef2f2;
}
.verify-chev {
  font-size: 9px;
  color: var(--text-faint);
  transition: transform 0.15s ease;
}
.verify-chev.open {
  transform: rotate(90deg);
}
.checks {
  list-style: none;
  margin: 6px 0 0;
  padding: 0;
}
.check {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 2px 0;
  font-size: 11px;
}
.check-mark {
  flex: 0 0 auto;
  font-family: var(--font-mono);
  font-size: 9.5px;
  font-weight: 700;
  padding: 0 5px;
  border-radius: 3px;
}
.check-mark.ok { color: #166534; background: #dcfce7; }
.check-mark.warn { color: #92400e; background: #fef3c7; }
.check-mark.bad { color: var(--status-error); background: #fef2f2; }
.check-name { font-family: var(--font-mono); color: var(--text); }
.check-detail { color: var(--text-faint); }
.repair-line {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px 8px;
  font-size: 11px;
  color: var(--text-muted);
}
.repair-tag {
  font-size: 9.5px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #92400e;
  background: #fef3c7;
  padding: 1px 6px;
  border-radius: var(--radius-pill);
}
.repair-name {
  font-family: var(--font-mono);
}
.feed-mode {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px 8px;
  border-top: 1px solid var(--border);
}
.feed-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-faint);
  margin-right: 2px;
}
.feed-btn {
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 2px 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  background: var(--surface);
  color: var(--text-muted);
  cursor: pointer;
}
.feed-btn.on {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent-hover);
  font-weight: 600;
}
.feed-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>
