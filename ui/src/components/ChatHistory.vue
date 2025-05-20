<template>
  <div
    ref="container"
    class="overflow-y-auto flex flex-col gap-4 h-full min-h-0"
    @scroll="onScroll"
  >
    <template v-for="(msg, idx) in visibleMessages" :key="idx">
      <!-- USER MESSAGE -->
      <div v-if="msg.role === 'user'" class="flex flex-col items-end gap-1 pr-2">
        <span class="text-xs font-semibold text-gray-500">User</span>
        <!-- user bubble -->
        <div class="mt-1 rounded relative group bg-gray-50 max-w-prose shadow">
          <!-- copy button -->
          <button
            class="!p-2 absolute top-2 right-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-white/80 hover:bg-white shadow-md rounded"
            v-tooltip="'Copy to Clipboard'"
            @click="copyToClipboard(msg.content)"
          >
            <i class="pi pi-copy"></i>
          </button>

          <pre
            class="bg-transparent text-gray-800 text-sm p-4 pr-12 overflow-x-auto font-mono whitespace-pre-wrap leading-snug"
          ><code>{{ msg.content }}</code></pre>
        </div>
      </div>

      <!-- ASSISTANT MESSAGE -->
      <div v-else-if="msg.role === 'assistant'" class="flex flex-col items-start gap-1 pl-2">
        <span class="text-xs font-semibold text-gray-500">text2cypher</span>

        <!-- inline assistant card -->
        <div class="mt-1 rounded relative group bg-gray-50">
          <!-- copy button -->
          <button
            class="!p-2 absolute top-2 right-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-white/80 hover:bg-white shadow-md rounded"
            v-tooltip="'Copy to Clipboard'"
            @click="copyToClipboard(msg.content)"
          >
            <i class="pi pi-copy"></i>
          </button>

          <!-- run query button -->
          <button
            class="!p-2 absolute top-2 right-12 opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-white/80 hover:bg-white shadow-md rounded"
            v-tooltip="'Run Query'"
            @click="emitRun(stripFences(msg.content))"
          >
            <i class="pi pi-play"></i>
          </button>

          <!-- cypher body -->
          <pre
            class="bg-transparent text-gray-800 text-sm p-4 pr-20 overflow-x-auto font-mono whitespace-pre-wrap leading-snug"
          ><code>{{ stripFences(msg.content) }}</code></pre>
        </div>
      </div>

      <!-- QUERY RESULT MESSAGE -->
      <div v-else class="flex flex-col items-start gap-1 pl-2">
        <span class="text-xs font-semibold text-gray-500">result</span>
        <pre class="bg-gray-50 p-4 rounded text-xs whitespace-pre-wrap font-mono shadow">
{{ msg.content }}
        </pre>
      </div>
    </template>
  </div>
</template>

<script setup>
import { nextTick, ref, watch, computed } from 'vue'
import { useToast } from 'primevue/usetoast'

const emit = defineEmits(['run-query'])
const props = defineProps({ messages: Array })
const container = ref(null)
const isAtBottom = ref(true)
const MIN_VISIBLE = 8
const count = ref(Math.min(props.messages.length, MIN_VISIBLE))
const visibleMessages = computed(() => props.messages.slice(-count.value))


const toast = useToast()

// helper — scroll container to very bottom
function scrollToBottom() {
  if (container.value) {
    container.value.scrollTop = container.value.scrollHeight
  }
}

function stripFences(text = '') {
  return text.replace(/^```(?:cypher)?/i, '').replace(/```$/, '').trim()
}

function emitRun(cypher) {
  emit('run-query', cypher)
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(stripFences(text))
    toast.add({ severity: 'success', summary: 'Copied', detail: 'Cypher query copied.', life: 2000 })
  } catch (err) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to copy.', life: 2000 })
  }
}

watch(
  () => props.messages.length,
  async (len, old) => {
    const added = len > old                                   // new messages arrived

    // keep list size under control
    if (isAtBottom.value) {
      // user is at bottom → collapse to latest MIN_VISIBLE messages
      count.value = Math.min(len, Math.max(MIN_VISIBLE, count.value))
    } else if (added) {
      // user is reading up → just append the new ones
      count.value = Math.min(len, count.value + (len - old))
    }

    // auto‑scroll when we’re supposed to stick to the bottom
    if (added && isAtBottom.value) {
      await nextTick()
      scrollToBottom()
    }
  }
)

function onScroll() {
  if (!container.value) return

  // Detect if user is at (or very near) the bottom
  const threshold = 10
  isAtBottom.value =
    container.value.scrollTop + container.value.clientHeight >=
    container.value.scrollHeight - threshold

  // Lazy‑load older messages when scrolled to the very top
  if (container.value.scrollTop === 0 && count.value < props.messages.length) {
    count.value = Math.min(props.messages.length, count.value + 4)
    nextTick(() => { if (container.value) container.value.scrollTop = 1 })
  }
}
</script>
