<script setup lang="ts">
import { state } from "../store";
import Panel from "./Panel.vue";
import PhaseNode from "./PhaseNode.vue";
</script>

<template>
  <Panel title="Pipeline">
    <div class="tree">
      <PhaseNode
        v-for="(phase, i) in state.pipeline"
        :key="phase.id"
        :phase="phase"
        :ordinal="i + 1"
      />
      <p v-if="state.pipeline.length === 0" class="empty">Waiting for pipeline…</p>
    </div>
  </Panel>
</template>

<style scoped>
.tree {
  padding: 8px;
}
.empty {
  padding: 16px;
  color: var(--text-faint);
  font-size: 13px;
}
</style>
