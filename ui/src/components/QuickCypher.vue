<template>
  <div class="p-4 text-sm overflow-y-auto h-full flex flex-col gap-4">
    <h1 class="text-lg font-semibold">Quick Cypher</h1>
    <div v-for="(cypher, idx) in scripts" :key="idx" class="flex flex-col items-start gap-1">
      <MessageBubble
        :text="cypher"
        :showRun="true"
        @run="emit('run-query', cypher)"
        @copy="copyToClipboard(cypher)"
      />
    </div>
  </div>
</template>

<script setup>
import MessageBubble from './MessageBubble.vue'
import { useToast } from 'primevue/usetoast'

const emit = defineEmits(['run-query'])
const toast = useToast()

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    toast.add({ severity: 'success', summary: 'Copied', life: 1500 })
  }).catch(() => {
    toast.add({ severity: 'error', summary: 'Copy failed', life: 1500 })
  })
}

const scripts = [
  'CALL db.schema.visualization',
  'SHOW CONSTRAINTS',
  'SHOW INDEXES',
  'MATCH (n) RETURN n LIMIT 25'
]
</script>
