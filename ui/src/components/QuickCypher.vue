<template>
  <div class="p-4 text-sm overflow-y-auto h-full flex flex-col">
    <h1 class="text-lg font-semibold">Quick Cypher</h1>
    <div
      v-for="(item, idx) in scripts"
      :key="idx"
      class="flex flex-col items-start gap-2 mt-6 first:mt-0"
    >
      <span class="text-sm font-semibold text-gray-700">
        {{ item.desc }}
      </span>
      <MessageBubble
        :text="item.query"
        :showRun="true"
        @run="emit('run-query', item.query)"
        @copy="copyToClipboard(item.query)"
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
  {
    query: 'CALL db.schema.visualization',
    desc: 'Visualize the database schema'
  },
  {
    query: 'MATCH (n) RETURN labels(n)[0], count(*)',
    desc: 'Count nodes by label'
  },
  {
    query: 'MATCH ()-[r]->() RETURN type(r), count(*)',
    desc: 'Count relationships by type'
  }
]
</script>
