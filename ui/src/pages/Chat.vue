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
          @clear="clearHistory"
          @update:useRemote="useRemote = $event"
        />

        <ChatHistory :messages="messages" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';
import axios from 'axios';
import QueryForm from '../components/QueryForm.vue';
import ChatHistory from '../components/ChatHistory.vue';

const query = ref('');
const messages = ref([]);
const loading = ref(false);
const useRemote = ref(false);         // ← remote (Assistant) flag

async function askAgent() {
  if (!query.value.trim()) return;

  const question = query.value;
  messages.value.push({ role: 'user', content: question });
  query.value = '';
  loading.value = true;

  const endpoint = useRemote.value ? '/api/remote/ask' : '/api/local/ask';

  try {
    const res = await axios.post(endpoint, { query: question });
    const ans = res.data.answer || 'No response received.';
    messages.value.push({ role: 'assistant', content: ans });
  } catch (err) {
    messages.value.push({
      role: 'assistant',
      content: 'Error: ' + (err.response?.data?.detail || err.message || 'Unknown error.')
    });
  } finally {
    loading.value = false;
  }
}

async function loadHistory() {
  if (useRemote.value) {
    messages.value = [];
    return;
  }
  try {
    const res = await axios.get('/api/local/history');
    messages.value = res.data.history || [];
  } catch {
    messages.value = [];
  }
}

async function clearHistory() {
  messages.value = [];
  if (!useRemote.value) {
    try {
      await axios.post('/api/local/clear');
    } catch {}
  }
}

onMounted(loadHistory);
watch(useRemote, loadHistory);
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