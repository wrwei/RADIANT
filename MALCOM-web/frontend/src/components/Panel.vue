<script setup lang="ts">
defineProps<{ title: string }>();
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <span class="section-title">{{ title }}</span>
      <div class="panel-actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="panel-body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}
.panel-head {
  flex: 0 0 auto;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  border-bottom: 1px solid var(--border);
  background: var(--surface-2);
}
.panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.panel-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}
</style>
