<!-- ui/src/components/MessageBubble.vue -->
<template>
  <div class="relative group w-full">
    <div class="flex gap-2">
      <!-- Message content with background -->
      <div class="flex-1 bg-gray-50 rounded-lg px-4 py-3">
        <pre
          v-if="isCode"
          class="text-gray-800 text-sm font-mono whitespace-pre-wrap leading-relaxed m-0"
        ><code>{{ text }}</code></pre>
        <p
          v-else
          class="text-gray-800 text-sm whitespace-pre-wrap leading-relaxed m-0"
        >{{ text }}</p>
      </div>
      
      <!-- Action buttons -->
      <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          v-if="showRun"
          class="p-1.5 h-7 w-7 flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
          @click="$emit('run', text)"
          title="Open in Neo4j Browser"
        >
          <i class="pi pi-play text-xs"></i>
        </button>
        <button
          class="p-1.5 h-7 w-7 flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
          @click="$emit('copy', text)"
          title="Copy to Clipboard"
        >
          <i class="pi pi-copy text-xs"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  text: String,
  showRun: { type: Boolean, default: false },
})

// Detect if content looks like code (simple heuristic)
const isCode = computed(() => {
  return props.showRun || props.text.includes('MATCH') || props.text.includes('RETURN')
})
</script>