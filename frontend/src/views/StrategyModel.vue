<template>
  <!-- "How this works": src/content/strategy-model.md, with the validation numbers from
       manifest.json (tyre_model) filled into its {{placeholders}}. -->
  <main class="about">
    <a class="about-back" href="#" @click.prevent="router.back()">← BACK</a>
    <article class="md" v-html="html"></article>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import source from '@/content/strategy-model.md?raw'
import { renderMarkdown } from '@/lib/markdown'
import { getManifest } from '@/services/data'
import { SIM_RUNS } from '@/lib/strategySim'

const router = useRouter()
const numbers = ref({})
onMounted(async () => {
  try {
    const summary = (await getManifest()).tyre_model || {}
    numbers.value = { ...summary, ...(summary.confidence || {}) }
  } catch { /* the page still reads without the numbers: placeholders show as "…" */ }
})
const html = computed(() => renderMarkdown(source, { runs: SIM_RUNS, ...numbers.value }))
</script>

<style scoped>
.about { max-width: 760px; margin: 0 auto; padding: 2rem 1.5rem 4rem; color: var(--text-primary); }
.about-back { font-family: 'DM Mono', monospace; font-size: 0.62rem; letter-spacing: 0.16em; color: var(--text-secondary); text-decoration: none; }
.about-back:hover { color: var(--accent); }

.md :deep(h1) { margin: 1rem 0 0.8rem; font-family: 'Bebas Neue', sans-serif; font-weight: 400; font-size: clamp(2.2rem, 6vw, 3.4rem); line-height: 1; letter-spacing: 0.03em; }
.md :deep(h2) { margin: 2.2rem 0 0.6rem; padding-top: 0.9rem; border-top: 1px solid var(--border-primary); font-family: 'Bebas Neue', sans-serif; font-weight: 400; font-size: 1.6rem; letter-spacing: 0.05em; }
.md :deep(p), .md :deep(li) { font-family: 'Work Sans', sans-serif; font-size: 0.95rem; line-height: 1.65; color: var(--text-primary); }
.md :deep(p) { margin: 0.7rem 0; }
.md :deep(ul) { margin: 0.7rem 0; padding-left: 1.2rem; }
.md :deep(li) { margin: 0.35rem 0; }
.md :deep(strong) { font-weight: 600; }
.md :deep(a) { color: var(--accent-hover); }
.md :deep(code) { font-family: 'DM Mono', monospace; font-size: 0.85em; }
.md :deep(pre) { margin: 0.9rem 0; padding: 0.8rem 0.9rem; border: 1px solid var(--border-secondary); background: var(--bg-card); overflow-x: auto; }
.md :deep(pre code) { font-size: 0.8rem; color: var(--text-primary); }
.md :deep(.md-table) { margin: 0.9rem 0; overflow-x: auto; }
.md :deep(table) { width: 100%; border-collapse: collapse; font-family: 'Work Sans', sans-serif; font-size: 0.88rem; }
.md :deep(th) { text-align: left; font-family: 'DM Mono', monospace; font-weight: 400; font-size: 0.6rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--text-secondary); }
.md :deep(th), .md :deep(td) { padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--border-primary); }
.md :deep(td:last-child) { font-family: 'DM Mono', monospace; white-space: nowrap; }

@media (max-width: 720px) {
  .about { padding: 1.25rem 1rem 3rem; }
}
</style>
