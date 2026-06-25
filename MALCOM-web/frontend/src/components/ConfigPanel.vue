<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { state, setRunConfig, closeConfig } from "../store";

// Local form state — changes apply only on Save.
const localModel = ref(state.selectedModel);
const localMode = ref(state.agentMode);

function syncFromState(): void {
  localModel.value = state.selectedModel || state.models[0]?.key || "";
  localMode.value = state.agentMode;
}

// Re-sync from the store whenever the panel (re)opens.
watch(() => state.configOpen, (open) => { if (open) syncFromState(); });
// The model list may arrive (via /api/models) after the panel opens — default
// the selection in once it does.
watch(
  () => [state.selectedModel, state.models.length],
  () => { if (state.configOpen && !localModel.value) syncFromState(); },
);

// The model currently selected, shown explicitly so it's clear which LLM runs.
const currentName = computed(() => {
  const key = localModel.value || state.selectedModel;
  const m = state.models.find((x) => x.key === key);
  return m ? `${m.name} (${m.key})` : (key || "—");
});

function save(): void {
  setRunConfig(localModel.value, localMode.value);
  closeConfig();
}
</script>

<template>
  <div class="cfg-overlay" @click.self="closeConfig()">
    <div class="cfg-modal">
      <header class="cfg-head">
        <strong>Configuration</strong>
        <button class="cfg-x" title="Close" @click="closeConfig()">✕</button>
      </header>

      <div class="cfg-body">
        <div class="cfg-field">
          <label>Agent mode</label>
          <div class="seg">
            <button :class="{ on: localMode === 'multi' }" @click="localMode = 'multi'">
              Multi-agent
            </button>
            <button :class="{ on: localMode === 'single' }" @click="localMode = 'single'">
              Single agent
            </button>
          </div>
          <p class="cfg-hint">
            {{ localMode === 'single'
              ? 'One direct LLM call with the stage\'s primary agent (paper §4 Single-Agent baseline) — then verification, no repair loop.'
              : 'Full generate–check–refactor–trace group chat, with the verify–repair gate.' }}
          </p>
        </div>

        <div class="cfg-field">
          <label for="cfg-model">LLM model</label>
          <select id="cfg-model" v-model="localModel">
            <option v-if="!state.models.length" value="" disabled>
              No models found — is the server up to date?
            </option>
            <option v-for="m in state.models" :key="m.key" :value="m.key">
              {{ m.key }} — {{ m.name }}
            </option>
          </select>
          <p class="cfg-hint">
            Currently: <strong>{{ currentName }}</strong> · applies to the next stage you run.
          </p>
        </div>
      </div>

      <footer class="cfg-foot">
        <button class="btn btn-sm" @click="closeConfig()">Cancel</button>
        <button class="btn btn-sm btn-primary" @click="save()">Save</button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.cfg-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(20, 22, 30, 0.42);
  display: grid;
  place-items: center;
}
.cfg-modal {
  width: 440px;
  max-width: calc(100vw - 32px);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius, 12px);
  box-shadow: var(--shadow-lg, 0 16px 48px rgba(0, 0, 0, 0.22));
  overflow: hidden;
}
.cfg-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
}
.cfg-x {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-muted);
}
.cfg-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.cfg-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.cfg-field label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
}
.cfg-hint {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.45;
  color: var(--text-muted);
}
.seg {
  display: inline-flex;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  overflow: hidden;
  width: fit-content;
}
.seg button {
  border: none;
  background: var(--surface);
  cursor: pointer;
  padding: 7px 16px;
  font-size: 13px;
  font-family: inherit;
  color: var(--text-muted);
}
.seg button.on {
  background: var(--accent);
  color: #fff;
}
.cfg-field select {
  font-family: inherit;
  font-size: 13px;
  color: var(--text);
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  padding: 7px 10px;
}
.cfg-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 16px;
  border-top: 1px solid var(--border);
}
.btn-primary {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
</style>
