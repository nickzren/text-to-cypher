<!-- ui/src/components/ChatHistory.vue -->
<template>
  <div class="flex flex-col gap-4">
    <template v-for="(msg, idx) in messages" :key="idx">
      <!-- USER MESSAGE -->
      <div
        v-if="msg.role === 'user'"
        class="flex flex-col items-start gap-1"
      >
        <span class="text-xs font-semibold text-gray-500">User</span>
        <MessageBubble
          :text="msg.content"
          :showRun="false"
          :isAssistant="false"
          @copy="copyToClipboard"
        />
      </div>

      <!-- ASSISTANT (text2cypher) MESSAGE -->
      <div
        v-else-if="msg.role === 'assistant'"
        class="flex flex-col items-start gap-1"
      >
        <span class="text-xs font-semibold text-gray-500">
          text2cypher{{ getModelLabel(msg.provider) }}
        </span>
        <MessageBubble
          :text="stripFences(msg.content)"
          :showRun="true"
          :isAssistant="true"
          @run="emit('run-query', stripFences(msg.content))"
          @copy="copyToClipboard"
        />
      </div>

      <!-- RESULT MESSAGE (API JSON or error) -->
      <div v-else class="flex flex-col items-start gap-1">
        <span class="text-xs font-semibold text-gray-500">result</span>
        <pre
          class="bg-gray-50 p-3 rounded text-xs whitespace-pre font-mono w-full"
        >{{ msg.content }}</pre>
      </div>
    </template>
  </div>
</template>

<script setup>
import { useToast } from 'primevue/usetoast'
import MessageBubble from './MessageBubble.vue'

/* props / emits ----------------------------------------------------- */
const emit = defineEmits(['run-query'])
const props = defineProps({ messages: Array })

/* helpers ----------------------------------------------------------- */
const toast = useToast()

function getModelLabel(provider) {
  const labels = {
    'openai': ' (o4-mini)',
    'assistant': ' (OpenAI Assistant)',
    'google': ' (Gemini 2.5 Pro)'
  }
  return labels[provider] || ''
}

function stripFences(text = '') {
  return text.replace(/^```(?:cypher)?/i, '').replace(/```$/, '').trim()
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(stripFences(text))
    toast.add({ severity: 'success', summary: 'Copied', life: 1500 })
  } catch {
    toast.add({ severity: 'error', summary: 'Copy failed', life: 1500 })
  }
}
</script>