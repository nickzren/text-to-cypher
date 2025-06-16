<template>
  <div class="mt-1 rounded-xl relative group bg-gray-50 shadow p-4 w-full max-w-none">
    <!-- run-query button (optional) -->
    <button
      v-if="showRun"
      class="!p-2 absolute top-2 right-12 opacity-0 group-hover:opacity-100
             transition-opacity duration-200 bg-white/80 hover:bg-white shadow-md rounded"
      @click="$emit('run', text)"
      title="Open in Neo4j Browser"
    >
      <i class="pi pi-play"></i>
    </button>

    <!-- copy button -->
    <button
      class="!p-2 absolute top-2 right-3 opacity-0 group-hover:opacity-100
             transition-opacity duration-200 bg-white/80 hover:bg-white shadow-md rounded"
      @click="$emit('copy', text)"
      title="Copy to Clipboard"
    >
      <i class="pi pi-copy"></i>
    </button>

    <!-- code block -->
    <pre
      class="bg-transparent text-gray-800 text-base overflow-x-auto font-mono whitespace-pre-wrap leading-snug"
    ><code>{{ text }}</code></pre>
  </div>
</template>

<script setup>
defineProps({
  text: String,
  showRun: { type: Boolean, default: false },
})
</script>