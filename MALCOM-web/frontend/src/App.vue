<script setup lang="ts">
import { computed } from "vue";
import { state, selectCaseStudy, openThread, openConfig } from "./store";
import { useSocket } from "./composables/useSocket";
import { useResizable } from "./composables/useResizable";
import PipelinePanel from "./components/PipelinePanel.vue";
import DialoguePanel from "./components/DialoguePanel.vue";
import ArchivePanel from "./components/ArchivePanel.vue";
import ThreadLoom from "./components/ThreadLoom.vue";
import ConfigPanel from "./components/ConfigPanel.vue";

useSocket();
const { leftWidth, rightWidth, startDrag } = useResizable();

const gridStyle = computed(() => ({
  gridTemplateColumns: `${leftWidth.value}px 7px minmax(380px, 1fr) 7px ${rightWidth.value}px`,
}));

function onCaseStudy(e: Event): void {
  selectCaseStudy((e.target as HTMLSelectElement).value);
}

const modelLabel = computed(() => state.selectedModel || "default");
const modeLabel = computed(() => (state.agentMode === "single" ? "Single" : "Multi"));
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <span class="brand-mark">RA</span>
        <div class="brand-text">
          <h1>RADIANT</h1>
          <p>Multi-agent model-driven engineering pipeline</p>
        </div>
      </div>

      <div class="topbar-controls">
        <label class="field">
          <span>Case study</span>
          <select :value="state.selectedCaseStudy" @change="onCaseStudy">
            <option
              v-for="cs in state.caseStudies"
              :key="cs.config_path"
              :value="cs.config_path"
            >
              {{ cs.name }}
            </option>
          </select>
        </label>

        <span class="conn" :class="{ on: state.connected }">
          <span class="conn-dot" />
          {{ state.connected ? "Connected" : "Reconnecting…" }}
        </span>

        <button
          class="btn btn-sm cfg-btn"
          :title="`Configure agent mode and LLM model (current: ${modeLabel} · ${modelLabel})`"
          @click="openConfig()"
        >
          ⚙ Settings
        </button>

        <button class="btn btn-sm" @click="openThread()">Digital Thread</button>
      </div>
    </header>

    <main class="layout" :style="gridStyle">
      <PipelinePanel />
      <div class="splitter" @pointerdown="(e) => startDrag('left', e)" />
      <DialoguePanel />
      <div class="splitter" @pointerdown="(e) => startDrag('right', e)" />
      <ArchivePanel />
    </main>

    <ThreadLoom v-if="state.thread.open" />
    <ConfigPanel v-if="state.configOpen" />
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* ---- Top bar ---- */
.topbar {
  height: var(--header-h);
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: linear-gradient(135deg, var(--accent), #7c73f0);
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.02em;
  display: grid;
  place-items: center;
  box-shadow: var(--shadow-sm);
}
.brand-text h1 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.06em;
}
.brand-text p {
  margin: 0;
  font-size: 11.5px;
  color: var(--text-muted);
}

.topbar-controls {
  display: flex;
  align-items: center;
  gap: 18px;
}
.field {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}
.field select {
  font-family: inherit;
  font-size: 13px;
  color: var(--text);
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  padding: 6px 28px 6px 10px;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%236b7280' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
}
.field select:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-ring);
}

.conn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  padding: 5px 11px;
  border-radius: var(--radius-pill);
  background: var(--surface-2);
  border: 1px solid var(--border);
}
.conn-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--status-error);
}
.conn.on {
  color: #047857;
  background: #ecfdf5;
  border-color: #d1fae5;
}
.conn.on .conn-dot {
  background: var(--status-completed);
}

/* ---- 3-pane layout ---- */
.layout {
  flex: 1 1 auto;
  display: grid;
  min-height: 0;
  padding: 14px;
  gap: 0;
}
.splitter {
  cursor: col-resize;
  position: relative;
}
.splitter::after {
  content: "";
  position: absolute;
  inset: 0 3px;
  border-radius: 2px;
  transition: background 0.15s;
}
.splitter:hover::after {
  background: var(--accent-ring);
}
</style>
