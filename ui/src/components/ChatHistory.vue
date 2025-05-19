<template>
  <div
    ref="container"
    class="overflow-y-auto flex flex-col gap-4 h-full"
    @scroll="onScroll"
  >
    <template v-for="(msg, idx) in visibleMessages" :key="idx">
      <div v-if="msg.role === 'user'" class="text-right">
        <Card class="shadow-2">
          <template #content>{{ msg.content }}</template>
        </Card>
      </div>
      <AnswerCard v-else :response="msg.content" />
    </template>
  </div>
</template>

<script setup>
import { nextTick, ref, watch, computed } from 'vue'
import Card from 'primevue/card'
import AnswerCard from './AnswerCard.vue'

const props = defineProps({ messages: Array })
const container = ref(null)
const count = ref(2)
const visibleMessages = computed(() => props.messages.slice(-count.value))

watch(
  () => props.messages.length,
  async (len, old) => {
    if (len > old) {
      count.value = Math.min(len, count.value + (len - old))
    }
    await nextTick()
    if (container.value) {
      container.value.scrollTop = container.value.scrollHeight
    }
  }
)

function onScroll() {
  if (!container.value) return
  if (container.value.scrollTop === 0 && count.value < props.messages.length) {
    count.value = Math.min(props.messages.length, count.value + 2)
    nextTick(() => {
      if (container.value) container.value.scrollTop = 1
    })
  }
}
</script>

