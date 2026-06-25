<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";
import { state } from "../store";

// Tick once a second so the elapsed counter updates while an agent works.
const now = ref(Date.now());
const timer = window.setInterval(() => (now.value = Date.now()), 1000);
onUnmounted(() => clearInterval(timer));

const show = computed(() => state.working.active || state.progress.active);

const elapsed = computed(() => {
  if (!state.working.startTime) return "";
  return ` · ${Math.floor((now.value - state.working.startTime) / 1000)}s`;
});

// Determinate when we know an overall total > 1 (sequential multi-requirement runs).
const determinate = computed(() => state.progress.active && state.progress.total > 1);
const pct = computed(() =>
  determinate.value
    ? Math.round((state.progress.current / state.progress.total) * 100)
    : 0,
);
const agentName = computed(() => state.progress.agent || state.working.agent);

const label = computed(() => {
  if (state.progress.active && state.progress.total > 1) {
    return `${state.progress.phase} · requirement ${state.progress.current}/${state.progress.total} · ${agentName.value} working…${elapsed.value}`;
  }
  return `${agentName.value} working…${elapsed.value}`;
});
</script>

<template>
  <transition name="fade">
    <div v-if="show" class="working">
      <span class="bar" :class="{ determinate }">
        <span
          class="fill"
          :style="determinate ? { width: pct + '%', left: '0', animation: 'none' } : {}"
        />
      </span>
      <span class="label">{{ label }}</span>
      <span v-if="determinate" class="pct">{{ pct }}%</span>
    </div>
  </transition>
</template>

<style scoped>
.working {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 16px 10px;
  padding: 8px 12px;
  background: var(--accent-soft);
  border: 1px solid var(--accent-ring);
  border-radius: var(--radius-sm);
}
.label {
  flex: 1 1 auto;
  font-size: 12.5px;
  color: var(--accent-hover);
  font-weight: 500;
}
.pct {
  flex: 0 0 auto;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--accent-hover);
}
.bar {
  position: relative;
  width: 64px;
  height: 4px;
  border-radius: 2px;
  background: #dcd9fb;
  overflow: hidden;
}
.bar.determinate {
  width: 120px;
}
.fill {
  position: absolute;
  left: -40%;
  width: 40%;
  height: 100%;
  border-radius: 2px;
  background: var(--accent);
  animation: slide 1.1s ease-in-out infinite;
  transition: width 0.3s ease;
}
@keyframes slide {
  0% {
    left: -40%;
  }
  100% {
    left: 100%;
  }
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
