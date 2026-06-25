<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";
import { state, previewFile, clearOutput } from "../store";
import Panel from "./Panel.vue";
import { previewHtml } from "../lib/format";

const confirming = ref(false);
let confirmTimer: ReturnType<typeof setTimeout> | null = null;

const previewBody = computed(() =>
  state.preview ? previewHtml(state.preview.path, state.preview.content) : "",
);

function onClear(): void {
  if (confirming.value) {
    if (confirmTimer) clearTimeout(confirmTimer);
    confirming.value = false;
    clearOutput(state.selectedTask || "");
  } else {
    confirming.value = true;
    confirmTimer = setTimeout(() => (confirming.value = false), 3000);
  }
}

onUnmounted(() => {
  if (confirmTimer) clearTimeout(confirmTimer);
});
</script>

<template>
  <Panel title="Archive">
    <template #actions>
      <span v-if="state.fileTask" class="ctx">{{ state.fileTask }}</span>
      <button class="btn btn-sm clear" :class="{ confirm: confirming }" @click="onClear">
        {{ confirming ? "Confirm?" : "Clear" }}
      </button>
    </template>

    <div class="archive">
      <div class="files">
        <button
          v-for="f in state.fileList"
          :key="f"
          class="file"
          :class="{ selected: state.preview?.path === f }"
          @click="previewFile(f)"
        >
          <span class="f-icon">▢</span>
          <span class="f-name">{{ f }}</span>
        </button>
        <p v-if="state.fileList.length === 0" class="empty">
          No output files yet. Select a stage to list its artefacts.
        </p>
      </div>

      <div class="preview">
        <div v-if="state.preview" class="prev-head">{{ state.preview.path }}</div>
        <pre v-if="state.preview" class="prev-body"><code class="hljs" v-html="previewBody" /></pre>
        <p v-else class="empty pad">Click a file to preview it.</p>
      </div>
    </div>
  </Panel>
</template>

<style scoped>
.ctx {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
}
.clear.confirm {
  color: var(--status-error);
  border-color: #f3c2c2;
  background: #fef2f2;
  animation: blink 0.7s steps(2, start) infinite;
}
@keyframes blink {
  50% {
    opacity: 0.55;
  }
}
.archive {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.files {
  flex: 0 0 auto;
  max-height: 42%;
  overflow: auto;
  padding: 8px;
  border-bottom: 1px solid var(--border);
}
.file {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  border: 1px solid transparent;
  padding: 6px 9px;
  border-radius: var(--radius-sm);
  text-align: left;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
}
.file:hover {
  background: var(--surface-hover);
}
.file.selected {
  background: var(--accent-soft);
  border-color: var(--accent-ring);
  color: var(--accent);
}
.f-icon {
  font-size: 10px;
}
.f-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.preview {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.prev-head {
  flex: 0 0 auto;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  background: var(--surface-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.prev-body {
  flex: 1 1 auto;
  min-height: 0;
  margin: 0;
  overflow: auto;
  padding: 10px 12px;
}
.prev-body code {
  background: transparent;
}
.empty {
  color: var(--text-faint);
  font-size: 12.5px;
}
.empty.pad,
.files .empty {
  padding: 14px;
}
</style>
