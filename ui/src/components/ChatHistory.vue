<template>
  <div
    ref="container"
    class="overflow-y-auto flex flex-col gap-4 h-full min-h-0"
    @scroll="onScroll"
  >
    <template v-for="(msg, idx) in visibleMessages" :key="idx">
      <!-- USER MESSAGE -->
      <div
        v-if="msg.role === 'user'"
        class="flex flex-col items-start gap-1 pl-2"
      >
        <span class="text-base font-semibold text-gray-500">User</span>
        <MessageBubble
          :text="msg.content"
          @copy="copyToClipboard"
        />
      </div>

      <!-- ASSISTANT (text2cypher) MESSAGE -->
      <div
        v-else-if="msg.role === 'assistant'"
        class="flex flex-col items-start gap-1 pl-2"
      >
        <span class="text-base font-semibold text-gray-500">text2cypher</span>
        <MessageBubble
          :text="stripFences(msg.content)"
          :showRun="true"
          @run="emit('run-query', stripFences(msg.content))"
          @copy="copyToClipboard"
        />
      </div>

      <!-- RESULT MESSAGE (API JSON or error) -->
      <div v-else class="flex flex-col items-start gap-1 pl-2">
        <span class="text-xs font-semibold text-gray-500">result</span>
        <pre
          class="bg-gray-50 p-4 rounded text-xs whitespace-pre font-mono shadow"
        >{{ msg.content }}</pre>
      </div>
    </template>
  </div>
</template>

<script setup>
/* ------------------------------------------------------------------ */
import { nextTick, ref, watch, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import MessageBubble from './MessageBubble.vue'

/* props / emits ----------------------------------------------------- */
const emit = defineEmits(['run-query'])
const props = defineProps({ messages: Array })

/* scrolling / lazy-load state -------------------------------------- */
const container = ref(null)
const isAtBottom = ref(true)
const MIN_VISIBLE = 8
const count = ref(Math.min(props.messages.length, MIN_VISIBLE))
const visibleMessages = computed(() => props.messages.slice(-count.value))

/* helpers ----------------------------------------------------------- */
const toast = useToast()

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

/* watch for new messages to autoscroll ----------------------------- */
watch(
  () => props.messages.length,
  async (len, old) => {
    const added = len > old
    if (isAtBottom.value) {
      count.value = Math.min(len, Math.max(MIN_VISIBLE, count.value))
    } else if (added) {
      count.value = Math.min(len, count.value + (len - old))
    }
    if (added && isAtBottom.value) {
      await nextTick()
      scrollToBottom()
    }
  }
)

/* scroll handlers --------------------------------------------------- */
function scrollToBottom() {
  if (container.value) container.value.scrollTop = container.value.scrollHeight
}

function onScroll() {
  if (!container.value) return
  const threshold = 10
  isAtBottom.value =
    container.value.scrollTop + container.value.clientHeight >=
    container.value.scrollHeight - threshold

  /* pull to load older messages */
  if (container.value.scrollTop === 0 && count.value < props.messages.length) {
    count.value = Math.min(props.messages.length, count.value + 4)
    nextTick(() => {
      if (container.value) container.value.scrollTop = 1
    })
  }
}
</script>

<style scoped>
/* no additional styles needed – rely on Tailwind utilities */
</style>