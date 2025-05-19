<template>
  <div class="w-full h-screen flex justify-center px-4 pt-10">
    <div class="w-full max-w-3xl flex flex-col gap-4 h-full">
      <div class="text-center">
        <div class="flex justify-center items-center mb-4">
          <img src="../assets/logo.png" alt="Logo" class="h-38 w-auto" />
        </div>
      </div>

      <QueryForm
        v-if="!inputAtBottom"
        v-model="query"
        :loading="loading"
        @submit="askAgent"
        @clear="clearHistory"
        @update:useRemote="useRemote = $event"
      />

      <ChatHistory
        :messages="messages"
        class="flex-1"
      />

      <QueryForm
        v-if="inputAtBottom"
        v-model="query"
        :loading="loading"
        class="sticky bottom-0 bg-white pt-3"
        @submit="askAgent"
        @clear="clearHistory"
        @update:useRemote="useRemote = $event"
      />
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
const inputAtBottom = ref(false);

async function askAgent() {
  if (!query.value.trim()) return;

  const question = query.value;
  messages.value.push({ role: 'user', content: question });
  inputAtBottom.value = true;
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
  const endpoint = useRemote.value ? '/api/remote/history' : '/api/local/history';
  try {
    const res = await axios.get(endpoint);
    messages.value = res.data.history || [];
    inputAtBottom.value = messages.value.length > 0;
  } catch {
    messages.value = [];
    inputAtBottom.value = false;
  }
}

async function clearHistory() {
  messages.value = [];
  inputAtBottom.value = false;
  const endpoint = useRemote.value ? '/api/remote/clear' : '/api/local/clear';
  try {
    await axios.post(endpoint);
  } catch {}
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