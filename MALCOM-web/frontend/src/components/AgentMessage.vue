<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { ChatMessage } from "../types";
import { formatJson } from "../lib/format";
import { state } from "../store";

const props = defineProps<{ msg: ChatMessage }>();

// Per-message fold state; a global Fold-all / Unfold-all pushes onto it.
const collapsed = ref(false);
watch(
  () => state.fold.signal,
  () => {
    collapsed.value = state.fold.collapsed;
  },
);

// Stable per-agent accent so messages are visually attributable.
const hue = computed(() => {
  const name = props.msg.agent || "";
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 360;
  return h;
});

const jsonHtml = computed(() => formatJson(props.msg.content));

// Repair agents (side agents) get a distinct tag so a repair attempt is obvious.
const isRepair = computed(() => {
  const a = props.msg.agent || "";
  return a.endsWith("_Repair_Agent") || a === "EOL_Repairer";
});

// One-line preview shown when the message is folded.
const preview = computed(() =>
  (props.msg.content || "")
    .replace(/```[a-zA-Z0-9]*/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 100),
);
</script>

<template>
  <div class="msg" :class="{ collapsed }">
    <div class="msg-head" @click="collapsed = !collapsed">
      <span class="chevron" :class="{ open: !collapsed }">▶</span>
      <span
        class="avatar"
        :style="{ background: `hsl(${hue} 70% 92%)`, color: `hsl(${hue} 55% 38%)` }"
      >
        {{ (msg.agent || "?").charAt(0) }}
      </span>
      <span class="agent">{{ msg.agent }}</span>
      <span v-if="isRepair" class="repair-badge">repair</span>
      <span v-if="msg.streaming" class="live">streaming</span>
      <span v-if="collapsed" class="preview">{{ preview }}</span>
    </div>
    <div v-show="!collapsed" class="body">
      <pre v-if="jsonHtml" class="json"><code class="hljs language-json" v-html="jsonHtml" /></pre>
      <p v-else class="text">{{ msg.content }}</p>
    </div>
  </div>
</template>

<style scoped>
.msg {
  margin: 10px 0;
}
.msg-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
  cursor: pointer;
  user-select: none;
}
.chevron {
  font-size: 9px;
  color: var(--text-faint);
  transition: transform 0.15s ease;
  width: 10px;
  flex: 0 0 auto;
}
.chevron.open {
  transform: rotate(90deg);
}
.avatar {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  flex: 0 0 auto;
}
.agent {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  flex: 0 0 auto;
}
.live {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 1px 7px;
  border-radius: var(--radius-pill);
  flex: 0 0 auto;
}
.repair-badge {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #92400e;
  background: #fef3c7;
  padding: 1px 7px;
  border-radius: var(--radius-pill);
  flex: 0 0 auto;
}
.preview {
  font-size: 11.5px;
  color: var(--text-faint);
  font-family: var(--font-mono);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1 1 auto;
  min-width: 0;
}
.body {
  margin-left: 30px;
}
.text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  color: var(--text);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 9px 11px;
}
.json {
  margin: 0;
  overflow: auto;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}
.json code {
  display: block;
  padding: 10px 12px;
  background: var(--surface-2);
}
</style>
