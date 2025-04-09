<template>
  <div class="w-full px-4 pt-10 flex justify-center">
    <div class="w-full max-w-3xl flex flex-col gap-4">
      <div class="text-center">
        <div class="flex justify-center items-center mb-4">
          <img src="../assets/logo.png" alt="Logo" class="h-38 w-auto" />
        </div>
      </div>

      <div class="flex flex-col gap-1">
        <QueryForm
          v-model="query"
          :loading="loading"
          @submit="askOpenAI"
          @update:useAssistant="useAssistant = $event"
        />

        <transition name="fade">
          <AnswerCard v-if="response" :response="response" />
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import axios from 'axios';
import QueryForm from '../components/QueryForm.vue';
import AnswerCard from '../components/AnswerCard.vue';

const query = ref('');
const response = ref('');
const loading = ref(false);
const useAssistant = ref(false);

async function askOpenAI() {
  if (!query.value.trim()) return;

  // Clear previous response immediately on submit
  response.value = '';
  loading.value = true;

  const endpoint = useAssistant.value ? '/api/assistant/ask' : '/api/ask';

  try {
    const res = await axios.post(endpoint, { query: query.value });
    response.value = res.data.answer || 'No response received.';
  } catch (err) {
    response.value =
      'Error: ' + (err.response?.data?.detail || err.message || 'Unknown error.');
  } finally {
    loading.value = false;
  }
}

// Clear response only when query input is cleared
watch(query, (newVal) => {
  if (!newVal.trim()) {
    response.value = '';
  }
});

// Clear response when switching API selection
watch(useAssistant, () => {
  response.value = '';
});
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>