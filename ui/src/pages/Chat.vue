<!-- ui/src/pages/Chat.vue -->
<template>
  <!-- ⚙️ desktop split‑view, mobile overlay -->
  <div class="h-screen flex overflow-hidden bg-white">
    <!-- 🄰  chat column (flex‑1) -->
    <section 
      class="flex flex-col h-full flex-1 max-w-none overflow-hidden"
      :style="{ paddingInline: chatMargin + 'px' }"
    >
      <!-- Header with logo and new chat button -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <img 
          src="../assets/logo.png" 
          alt="Text to Cypher" 
          class="h-13 w-auto" 
        />
        
        <button
          @click="clearHistory"
          class="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-colors"
        >
          <i class="pi pi-plus text-sm"></i>
          New Chat
        </button>
      </div>

      <!-- scrollable history -->
      <div class="flex-1 overflow-y-auto px-4 py-4">
        <ChatHistory
          :messages="messages"
          @run-query="runQuery"
        />
      </div>

      <!-- query form at bottom -->
      <div class="border-t border-gray-200 px-4 py-3">
        <QueryForm
          v-model="query"
          :loading="loading"
          :selectedProvider="selectedProvider"
          @submit="askAgent"
          @update:selectedProvider="selectedProvider = $event"
        />
      </div>
    </section>

    <!-- 🄱  drag handle (desktop only) -->
    <div
      v-show="!isMobile && sidebarVisible"
      class="w-px bg-gray-200 hover:bg-gray-300 cursor-col-resize transition-colors"
      @mousedown="startDrag"
    ></div>

    <!-- 🄲  side panel (schema / quick cypher) -->
    <aside
      v-show="sidebarVisible && (!isMobile || showSidebar)"
      :style="{ width: schemaWidth + 'px' }"
      class="border-l border-gray-200 overflow-y-auto bg-gray-50 h-full z-10 fixed top-0 right-0 sm:static sm:block"
    >
      <div class="border-b border-gray-200 bg-white sticky top-0 z-10">
        <div class="p-3 flex gap-1 items-center">
          <button
            class="flex-1 text-sm px-3 py-1.5 rounded transition-colors flex items-center justify-center gap-1"
            :class="sidebarTab === 'schema' 
              ? 'bg-sky-100 text-sky-700 font-medium' 
              : 'text-gray-600 hover:bg-gray-100'"
            @click="sidebarTab = 'schema'"
          >
            <i class="pi pi-sitemap text-xs"></i>
            <span>Schema</span>
          </button>
          <button
            class="flex-1 text-sm px-3 py-1.5 rounded transition-colors flex items-center justify-center gap-1"
            :class="sidebarTab === 'cypher' 
              ? 'bg-sky-100 text-sky-700 font-medium' 
              : 'text-gray-600 hover:bg-gray-100'"
            @click="sidebarTab = 'cypher'"
          >
            <i class="pi pi-code text-xs"></i>
            <span>Cypher</span>
          </button>
          <button 
            class="ml-2 p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors flex items-center justify-center" 
            @click="hideSidebar" 
            title="Close"
          >
            <i class="pi pi-times text-sm"></i>
          </button>
        </div>
      </div>
      <component
        :is="sidebarTab === 'schema' ? SchemaViewer : QuickCypher"
        class="h-full"
        @run-query="runQuery"
      />
    </aside>
  </div>

  <!-- Floating toggles for mobile when panel hidden -->
  <div v-if="isMobile && !showSidebar" class="fixed bottom-4 right-4 flex flex-col gap-2 z-20">
    <button
      @click="openSidebar('schema')"
      class="p-3 rounded-full shadow-lg bg-sky-600 text-white hover:bg-sky-700 transition-colors"
    >
      <i class="pi pi-book text-lg"></i>
    </button>
    <button
      @click="openSidebar('cypher')"
      class="p-3 rounded-full shadow-lg bg-sky-600 text-white hover:bg-sky-700 transition-colors"
    >
      <i class="pi pi-code text-lg"></i>
    </button>
  </div>

  <!-- desktop show button when hidden -->
  <button
    v-if="!isMobile && !sidebarVisible"
    @click="sidebarVisible = true"
    class="fixed top-1/2 right-0 p-2 rounded-l shadow-lg bg-sky-600 text-white hover:bg-sky-700 transition-colors"
  >
    <i class="pi pi-angle-left"></i>
  </button>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue';
import axios from 'axios';
import QueryForm from '../components/QueryForm.vue';
import ChatHistory from '../components/ChatHistory.vue';
import SchemaViewer from '../components/SchemaViewer.vue';
import QuickCypher from '../components/QuickCypher.vue';

const windowWidth = ref(window.innerWidth);
const CHAT_MIN_WIDTH = 320;   // px
const MAX_MARGIN     = 200;   // px (mx-50)

const schemaWidth   = ref(450); // px
const showSidebar   = ref(false);    // mobile overlay
const sidebarVisible = ref(true);    // desktop visibility
const sidebarTab     = ref('schema');
const isMobile    = ref(window.innerWidth < 640);
const SCHEMA_MIN_WIDTH = 200; // px

function onResize() {
  windowWidth.value = window.innerWidth;
  isMobile.value = window.innerWidth < 640;
  if (isMobile.value) {
    showSidebar.value = false;
    sidebarVisible.value = false;
  } else if (!sidebarVisible.value) {
    sidebarVisible.value = true;
  }
}

onMounted(() => {
  window.addEventListener('resize', onResize, { passive: true });
  onResize();
});

onUnmounted(() => window.removeEventListener('resize', onResize));

// Horizontal resizing for sidebar
function startDrag(e) {
  const startX     = e.clientX;
  const startWidth = schemaWidth.value;
  const onMove = ev => {
    schemaWidth.value = Math.max(SCHEMA_MIN_WIDTH, startWidth - (ev.clientX - startX));
  };
  const onUp = () => {
    window.removeEventListener('mousemove', onMove);
    window.removeEventListener('mouseup', onUp);
  };
  window.addEventListener('mousemove', onMove);
  window.addEventListener('mouseup', onUp);
}

const chatMargin = computed(() => {
  const sidebarWidth = sidebarVisible.value ? schemaWidth.value : 0;
  const leftover = windowWidth.value - sidebarWidth - CHAT_MIN_WIDTH;
  const half     = leftover / 2;
  if (half >= MAX_MARGIN) return MAX_MARGIN;
  return Math.max(16, half); // keep at least 16 px
});

const query = ref('');
const messages = ref(/** @type {{role:string,content:string,provider?:string}[]} */([]));
const loading = ref(false);
// remember last‑chosen provider across page refreshes
const selectedProvider = ref(localStorage.getItem('selectedProvider') || 'openai');
const sessionIdKey = 'sessionId';
let sid = localStorage.getItem(sessionIdKey);
if (!sid) {
  sid = crypto.randomUUID();
  localStorage.setItem(sessionIdKey, sid);
}
const sessionId = sid;

function runQuery(cypher) {
  if (!cypher.trim()) return;

  // Vite exposes env vars prefixed with VITE_
  const base = import.meta.env.VITE_BROWSER_URL;
  if (!base) {
    console.error('VITE_BROWSER_URL is not defined');
    return;
  }

  const url = `${base.replace(/\/$/, '')}/browser?cmd=edit&arg=${encodeURIComponent(cypher)}`;
  window.open(url, '_blank');
}

function openSidebar(tab) {
  sidebarTab.value = tab;
  if (isMobile.value) {
    showSidebar.value = true;
  } else {
    sidebarVisible.value = true;
  }
}

function hideSidebar() {
  if (isMobile.value) {
    showSidebar.value = false;
  } else {
    sidebarVisible.value = false;
  }
}

async function askAgent() {
  if (!query.value.trim()) return;

  const question = query.value;
  messages.value.push({ role: 'user', content: question });
  query.value = '';
  loading.value = true;

  const endpoint = selectedProvider.value === 'assistant' ? '/api/assistant/ask' : '/api/ask';
  const payload = {
    query: question,
    session_id: sessionId,
    ...(selectedProvider.value !== 'assistant' && { provider: selectedProvider.value })
  };

  try {
    const res = await axios.post(endpoint, payload);
    const ans = res.data.answer || 'No response received.';
    messages.value.push({ 
      role: 'assistant', 
      content: ans,
      provider: selectedProvider.value 
    });
  } catch (err) {
    messages.value.push({
      role: 'assistant',
      content: 'Error: ' + (err.response?.data?.error || err.message || 'Unknown error.'),
      provider: selectedProvider.value
    });
  } finally {
    loading.value = false;
  }
}

async function loadHistory() {
  // Always use the shared history endpoint
  const endpoint = `/api/history?session_id=${sessionId}`;
    
  try {
    const res = await axios.get(endpoint);
    messages.value = res.data.history || [];
  } catch {
    messages.value = [];
  }
}

async function clearHistory() {
  messages.value = [];
  // Use the shared clear endpoint
  const endpoint = '/api/clear';
  const payload = { session_id: sessionId };
  
  try {
    await axios.post(endpoint, payload);
  } catch {}
}

onMounted(loadHistory);
// No need to reload history when switching providers anymore
watch(selectedProvider, val => {
  localStorage.setItem('selectedProvider', val);
});
</script>

<style scoped>
.cursor-col-resize {
  user-select: none;
}
</style>