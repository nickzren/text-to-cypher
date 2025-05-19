<template>
  <div ref="container" class="overflow-y-auto max-h-96 flex flex-col gap-4">
    <template v-for="(msg, idx) in messages" :key="idx">
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
import { nextTick, ref, watch } from 'vue'
import Card from 'primevue/card'
import AnswerCard from './AnswerCard.vue'

const props = defineProps({ messages: Array })
const container = ref(null)

watch(
  () => props.messages.length,
  async () => {
    await nextTick()
    if (container.value) {
      container.value.scrollTop = container.value.scrollHeight
    }
  }
)
</script>

