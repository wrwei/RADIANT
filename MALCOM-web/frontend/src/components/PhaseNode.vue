<script setup lang="ts">
import { ref } from "vue";
import type { PipelinePhase } from "../types";
import { state, phaseStatus, selectRequirement } from "../store";
import TaskNode from "./TaskNode.vue";
import GradleCommand from "./GradleCommand.vue";

const props = defineProps<{ phase: PipelinePhase; ordinal: number }>();

// Auto-expand manual + LLM phases by default (gradle collapsed).
const open = ref(props.phase.type !== "gradle");

function cleanLabel(label: string): string {
  return (label || "").replace(/^\s*\d+\s*[—-]\s*/, "");
}
</script>

<template>
  <div class="phase">
    <button class="phase-head" :data-status="phaseStatus(phase)" @click="open = !open">
      <span class="ordinal">{{ String(ordinal).padStart(2, "0") }}</span>
      <span class="phase-label">{{ cleanLabel(phase.label) }}</span>
      <span class="status-dot" :class="phaseStatus(phase)" />
      <span class="chev" :class="{ open }">›</span>
    </button>

    <div v-show="open" class="phase-children">
      <!-- manual: requirement files -->
      <template v-if="phase.type === 'manual'">
        <button
          v-for="req in state.requirements"
          :key="req.path"
          class="req"
          :class="{ selected: req.path === state.selectedRequirement }"
          @click="selectRequirement(req.path)"
        >
          <span class="req-icon">▤</span>
          <span class="req-name">{{ req.name }}</span>
        </button>
        <p v-if="state.requirements.length === 0" class="muted">No requirement files.</p>
      </template>

      <!-- llm: tasks with agent rosters -->
      <template v-else-if="phase.type === 'llm'">
        <TaskNode v-for="t in phase.tasks || []" :key="t" :task="t" />
      </template>

      <!-- gradle: commands -->
      <template v-else-if="phase.type === 'gradle'">
        <GradleCommand v-for="c in phase.commands || []" :key="c" :command-id="c" />
      </template>
    </div>
  </div>
</template>

<style scoped>
.phase {
  margin-bottom: 4px;
}
.phase-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  background: transparent;
  border: none;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  text-align: left;
  transition: background 0.12s;
}
.phase-head:hover {
  background: var(--surface-hover);
}
.ordinal {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--text-faint);
  width: 20px;
}
.phase-head[data-status="running"] .ordinal {
  color: var(--status-running);
}
.phase-head[data-status="completed"] .ordinal {
  color: var(--status-completed);
}
.phase-label {
  flex: 1 1 auto;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}
.chev {
  color: var(--text-faint);
  font-size: 16px;
  transition: transform 0.15s;
}
.chev.open {
  transform: rotate(90deg);
}
.phase-children {
  padding: 2px 0 6px 20px;
}
.req {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  border: 1px solid transparent;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  text-align: left;
  color: var(--text-muted);
  font-size: 12.5px;
}
.req:hover {
  background: var(--surface-hover);
}
.req.selected {
  background: var(--accent-soft);
  border-color: var(--accent-ring);
  color: var(--accent);
  font-weight: 600;
}
.req-icon {
  font-size: 11px;
}
.muted {
  margin: 4px 10px;
  color: var(--text-faint);
  font-size: 12px;
}
</style>
