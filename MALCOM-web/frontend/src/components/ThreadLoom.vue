<script setup lang="ts">
import { computed, ref } from "vue";
import { state, closeThread, fetchThread, startCommand } from "../store";
import type { ThreadElemNode, ThreadReqNode } from "../types";

const PHASES = ["concept", "dsml", "model", "behaviour"];
const COLS = ["requirement", ...PHASES];
const LABELS: Record<string, string> = {
  requirement: "REQUIREMENT", concept: "CONCEPT", dsml: "DSML",
  model: "MODEL", behaviour: "BEHAVIOUR",
};

// layout geometry (kept in sync between the HTML node boxes and the SVG links)
const COL_W = 180, COL_GAP = 80, HEADER_H = 28, NODE_H = 30, NODE_GAP = 12;
const colX = (c: number) => c * (COL_W + COL_GAP);
const nodeY = (i: number) => HEADER_H + i * (NODE_H + NODE_GAP);

const g = computed(() => state.thread.data);
const hoverCid = ref<string | null>(null);
const selected = ref<{ title: string; req: string; desc: string; span: string } | null>(null);

const colIndex = (phase: string) => COLS.indexOf(phase);
const reqIndex = computed(() => {
  const m = new Map<string, number>();
  (g.value?.nodes.requirement ?? []).forEach((n, i) => m.set((n as ThreadReqNode).cid, i));
  return m;
});
const elemIndex = computed(() => {
  const m = new Map<string, number>();
  for (const p of PHASES) (g.value?.nodes[p] ?? []).forEach((n, i) => m.set((n as ThreadElemNode).key, i));
  return m;
});

const canvas = computed(() => {
  const maxNodes = Math.max(1, ...COLS.map((c) => g.value?.nodes[c]?.length ?? 0));
  return { w: colX(COLS.length - 1) + COL_W, h: HEADER_H + maxNodes * (NODE_H + NODE_GAP) };
});

interface LoomPath { d: string; impacted: boolean; active: boolean; }
const paths = computed<LoomPath[]>(() => {
  if (!g.value) return [];
  return g.value.links.map((l) => {
    const ri = reqIndex.value.get(l.from) ?? 0;
    const ei = elemIndex.value.get(l.to) ?? 0;
    const x1 = colX(0) + COL_W, y1 = nodeY(ri) + NODE_H / 2;
    const x2 = colX(colIndex(l.phase)), y2 = nodeY(ei) + NODE_H / 2;
    const cx = (x1 + x2) / 2;
    return {
      d: `M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`,
      impacted: l.impacted,
      active: hoverCid.value === null ? true : l.from === hoverCid.value,
    };
  });
});

// node-active set for dimming: when hovering a requirement, its elements stay lit
const activeKeys = computed(() => {
  if (!g.value || hoverCid.value === null) return null;
  const keys = new Set<string>();
  for (const l of g.value.links) if (l.from === hoverCid.value) keys.add(l.to);
  return keys;
});

function reqDim(n: ThreadReqNode): boolean {
  return hoverCid.value !== null && n.cid !== hoverCid.value;
}
function elemDim(n: ThreadElemNode): boolean {
  return activeKeys.value !== null && !activeKeys.value.has(n.key);
}
function spanOf(src: Record<string, unknown>): string {
  const f = src.file ?? "";
  if (src.line_start != null) return `${f}:${src.line_start}-${src.line_end}`;
  if (src.char_start != null) return `${f} char ${src.char_start}-${src.char_end}`;
  return String(f);
}
function pickReq(n: ThreadReqNode) {
  selected.value = { title: n.name, req: n.id, desc: n.description, span: "" };
}
function pickElem(n: ThreadElemNode) {
  const link = g.value?.links.find((l) => l.to === n.key);
  const req = g.value?.nodes.requirement.find((r) => (r as ThreadReqNode).cid === link?.from) as ThreadReqNode | undefined;
  selected.value = {
    title: n.label, req: req?.id ?? link?.from ?? "", desc: req?.description ?? "",
    span: link ? spanOf(link.source) : "",
  };
}
function hoverElem(n: ThreadElemNode) {
  hoverCid.value = g.value?.links.find((l) => l.to === n.key)?.from ?? null;
}
function runImpact() {
  startCommand("ciaReport");   // streams in the dialogue; phase_complete triggers auto-refresh
}
</script>

<template>
  <div class="loom-overlay">
    <header class="loom-bar">
      <div class="loom-title">
        <strong>Digital Thread</strong>
        <span class="loom-sub" v-if="g">{{ g.case_study }} · cross-phase traceability</span>
      </div>
      <div class="loom-actions">
        <button class="btn btn-sm" @click="fetchThread()" :disabled="state.thread.loading">Refresh</button>
        <button class="btn btn-sm" @click="runImpact()">Run change-impact</button>
        <button class="btn btn-sm" @click="closeThread()">✕ Close</button>
      </div>
    </header>

    <div class="loom-stats" v-if="g">
      <span>{{ g.stats.total_links }} links</span>
      <span v-for="p in PHASES" :key="p">{{ p }}: {{ g.stats.by_phase[p] ?? 0 }}
        ({{ Math.round((g.stats.coverage[p] ?? 0) * 100) }}%)</span>
    </div>

    <div class="loom-body" v-if="g">
      <div class="loom-canvas" :style="{ width: canvas.w + 'px', height: canvas.h + 'px' }">
        <svg class="loom-links" :width="canvas.w" :height="canvas.h">
          <defs>
            <marker id="loom-arrow" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill="#b9b1a4" />
            </marker>
            <marker id="loom-arrow-impacted" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill="#d2493b" />
            </marker>
          </defs>
          <path v-for="(p, i) in paths" :key="i" :d="p.d"
                class="loom-link" :class="{ impacted: p.impacted, dim: !p.active }"
                :marker-end="p.impacted ? 'url(#loom-arrow-impacted)' : 'url(#loom-arrow)'" />
        </svg>
        <!-- column headers -->
        <div v-for="(c, ci) in COLS" :key="'h' + c" class="loom-col-head"
             :style="{ left: colX(ci) + 'px', width: COL_W + 'px' }">{{ LABELS[c] }}</div>
        <!-- requirement nodes -->
        <div v-for="(n, i) in (g.nodes.requirement as ThreadReqNode[])" :key="n.cid"
             class="loom-node req" :class="{ dim: reqDim(n), untraced: !n.traced, impacted: n.impacted }"
             :style="{ left: colX(0) + 'px', top: nodeY(i) + 'px', width: COL_W + 'px', height: NODE_H + 'px' }"
             @mouseenter="hoverCid = n.cid" @mouseleave="hoverCid = null" @click="pickReq(n)">
          <span class="loom-node-id">{{ n.id }}</span>
        </div>
        <!-- phase element nodes -->
        <template v-for="p in PHASES" :key="p">
          <div v-for="(n, i) in (g.nodes[p] as ThreadElemNode[])" :key="n.key"
               class="loom-node elem" :class="{ dim: elemDim(n), impacted: n.impacted }"
               :style="{ left: colX(colIndex(p)) + 'px', top: nodeY(i) + 'px', width: COL_W + 'px', height: NODE_H + 'px' }"
               @mouseenter="hoverElem(n)" @mouseleave="hoverCid = null" @click="pickElem(n)">
            <span class="loom-node-id">{{ n.label }}</span>
          </div>
        </template>
        <div v-for="(c, ci) in PHASES" :key="'e' + c" v-show="(g.nodes[c]?.length ?? 0) === 0"
             class="loom-empty" :style="{ left: colX(ci + 1) + 'px', top: nodeY(0) + 'px', width: COL_W + 'px' }">
          No elements
        </div>
      </div>

      <aside class="loom-detail" v-if="selected">
        <button class="loom-detail-x" @click="selected = null">✕</button>
        <h4>{{ selected.title }}</h4>
        <p><strong>Requirement:</strong> {{ selected.req }}</p>
        <p v-if="selected.desc">{{ selected.desc }}</p>
        <p v-if="selected.span" class="loom-span">{{ selected.span }}</p>
      </aside>
    </div>

    <div class="loom-body" v-else>
      <p style="padding: 24px">{{ state.thread.loading ? "Loading…" : (state.thread.error || "No thread data.") }}</p>
    </div>
  </div>
</template>

<style scoped>
.loom-overlay { position: fixed; inset: 0; z-index: 50; background: #faf8f5;
  display: flex; flex-direction: column; }
.loom-bar { display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px; border-bottom: 1px solid #e7e1d8; }
.loom-title strong { font-size: 16px; } .loom-sub { margin-left: 10px; color: #8a8278; font-size: 12px; }
.loom-actions { display: flex; gap: 8px; }
.loom-stats { display: flex; gap: 18px; padding: 8px 16px; font-size: 12px; color: #6b645b;
  border-bottom: 1px solid #efeae2; }
.loom-body { flex: 1; overflow: auto; position: relative; display: flex; }
.loom-canvas { position: relative; margin: 16px; }
.loom-links { position: absolute; inset: 0; pointer-events: none; }
.loom-link { fill: none; stroke: #b9b1a4; stroke-width: 1.2; transition: opacity .12s; }
.loom-link.dim { opacity: 0.12; }
.loom-link.impacted { stroke: #d2493b; stroke-width: 1.8; }
.loom-col-head { position: absolute; top: 0; font-size: 11px; font-weight: 700; color: #8a8278;
  letter-spacing: .04em; text-align: center; }
.loom-node { position: absolute; display: flex; align-items: center; padding: 0 8px;
  border: 1px solid #d8d0c4; border-radius: 6px; background: #fff; font-size: 12px;
  cursor: pointer; overflow: hidden; transition: opacity .12s; box-sizing: border-box; }
.loom-node.req { background: #f3efe8; }
.loom-node.untraced { opacity: 0.45; border-style: dashed; }
.loom-node.dim { opacity: 0.2; }
.loom-node.impacted { border-color: #d2493b; color: #b53a2d; background: #fdecea; }
.loom-node-id { white-space: nowrap; text-overflow: ellipsis; overflow: hidden; }
.loom-empty { position: absolute; font-size: 12px; color: #b3a99c; text-align: center; }
.loom-detail { width: 280px; border-left: 1px solid #e7e1d8; padding: 16px; position: relative; }
.loom-detail-x { position: absolute; top: 8px; right: 8px; border: none; background: none; cursor: pointer; }
.loom-span { font-family: monospace; font-size: 11px; color: #6b645b; }
</style>
