<!-- ui/src/components/MessageBubble.vue -->
<template>
  <div class="relative group w-full">
    <!-- Message content with integrated buttons -->
    <div 
      class="flex-1 rounded-lg px-4 py-3"
      :class="isAssistant ? 'bg-gray-50' : 'bg-blue-50'"
    >
      <div class="flex items-start gap-3">
        <p class="text-gray-800 text-sm whitespace-pre-wrap leading-relaxed m-0 flex-1">{{ text }}</p>
        
        <!-- Action buttons inside the panel -->
        <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            v-if="showRun && isCypherCode"
            class="p-1.5 h-7 w-7 flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-white/50 rounded transition-all"
            @click="$emit('run', text)"
            title="Open in Neo4j Browser"
          >
            <i class="pi pi-play text-xs"></i>
          </button>
          <button
            class="p-1.5 h-7 w-7 flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-white/50 rounded transition-all"
            @click="$emit('copy', text)"
            title="Copy to Clipboard"
          >
            <i class="pi pi-copy text-xs"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  text: String,
  showRun: { type: Boolean, default: false },
  isAssistant: { type: Boolean, default: false }
})

// Only show run button if it's actually a Cypher query
const isCypherCode = computed(() => {
  if (!props.isAssistant) return false;
  
  const cypherKeywords = ['MATCH', 'RETURN', 'WHERE', 'CREATE', 'MERGE', 'DELETE', 'WITH', 'OPTIONAL'];
  const text = props.text.toUpperCase();
  
  // Check if text contains Cypher keywords and patterns
  return cypherKeywords.some(keyword => text.includes(keyword)) && 
         (text.includes('(') || text.includes('-[') || text.includes(']->'));
})
</script>

<style scoped>
/* Consistent text styling for all messages */
p {
  font-size: 0.875rem; /* 14px - same as text-sm */
  line-height: 1.5;
  color: #1f2937; /* text-gray-800 */
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
</style>