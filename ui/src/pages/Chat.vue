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
          @submit="askAgent"
          @update:useRemote="useRemote = $event"
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
const useRemote = ref(false);         // ← remote (Assistant) flag

async function askAgent() {
  if (!query.value.trim()) return;

  response.value = '';
  loading.value = true;

  const endpoint = useRemote.value ? '/api/remote/ask' : '/api/local/ask';

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

// Clear response when input cleared
watch(query, (val) => {
  if (!val.trim()) response.value = '';
});

// Clear when switching local/remote
watch(useRemote, () => (response.value = ''));
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