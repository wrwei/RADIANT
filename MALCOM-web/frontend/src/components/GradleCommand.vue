<script setup lang="ts">
import { computed } from "vue";
import { state, gradleDepMissing, startCommand } from "../store";

const props = defineProps<{ commandId: string }>();

const cmd = computed(() => state.gradleCommands[props.commandId] || {});
const label = computed(() => cmd.value.label || props.commandId);
const status = computed(() => state.phaseStatuses[props.commandId] || "idle");
const missing = computed(() => gradleDepMissing(props.commandId));
</script>

<template>
  <div class="gradle">
    <span class="g-label" :class="{ blocked: missing }">{{ label }}</span>
    <span v-if="missing" class="dep">needs {{ missing }}</span>
    <span class="status-dot" :class="status" />
    <button class="btn btn-sm" :disabled="!!missing" @click="startCommand(commandId)">Run</button>
  </div>
</template>

<style scoped>
.gradle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  margin: 4px 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}
.g-label {
  flex: 1 1 auto;
  font-size: 12.5px;
  color: var(--text);
}
.g-label.blocked {
  color: var(--text-faint);
}
.dep {
  font-size: 10.5px;
  color: var(--status-running);
  background: #fffbeb;
  border: 1px solid #fde8b5;
  padding: 1px 6px;
  border-radius: var(--radius-pill);
}
</style>
