<template>
  <!-- ⚙️ desktop split‑view, mobile overlay -->
  <div class="h-screen flex overflow-hidden">
    <!-- 🄰  chat column (flex‑1) -->
    <section class="flex flex-col h-full flex-1 max-w-none px-4 pt-10 mx-auto gap-4">
      <!-- header -->
      <div class="text-center">
        <div class="flex justify-center items-center mb-4">
          <img src="../assets/logo.png" alt="Logo" class="h-38 w-auto" />
        </div>
      </div>

      <!-- top query form (desktop) -->
      <QueryForm
        :style="{ marginInline: chatMargin + 'px' }"
        :class="inputAtBottom ? 'sticky bottom-0 bg-white pt-1 order-2' : 'order-0'"
        v-model="query"
        :loading="loading"
        :useRemote="useRemote"
        @submit="askAgent"
        @clear="clearHistory"
        @update:useRemote="useRemote = $event"
      />

      <!-- scrollable history -->
      <ChatHistory
        :messages="messages"
        class="flex-1 overflow-y-auto order-1"
        :style="{ marginInline: chatMargin + 'px' }"
        @run-query="runQuery"
      />

    </section>

    <!-- 🄱  drag handle (desktop only) -->
    <div
      v-show="!isMobile && sidebarVisible"
      class="w-2 cursor-col-resize bg-gray-200 hover:bg-gray-300"
      @mousedown="startDrag"
    ></div>

    <!-- 🄲  side panel (schema / quick cypher) -->
    <aside
      v-show="sidebarVisible && (!isMobile || showSidebar)"
      :style="{ width: schemaWidth + 'px' }"
      class="border-l overflow-y-auto bg-white h-full z-10 fixed top-0 right-0 sm:static sm:block"
    >
      <div class="border-b p-2 flex gap-2 items-center">
        <button
          class="text-sm px-2"
          :class="{ 'font-bold underline': sidebarTab === 'schema' }"
          @click="sidebarTab = 'schema'"
        >Schema</button>
        <button
          class="text-sm px-2"
          :class="{ 'font-bold underline': sidebarTab === 'cypher' }"
          @click="sidebarTab = 'cypher'"
        >Cypher</button>
        <button class="ml-auto text-xl px-2" @click="hideSidebar" title="Close">&times;</button>
      </div>
      <component
        :is="sidebarTab === 'schema' ? SchemaViewer : QuickCypher"
        class="h-full"
        @run-query="runQuery"
      />
    </aside>
  </div>

  <!-- Floating toggles for mobile when panel hidden -->
  <div v-if="isMobile && !showSidebar" class="fixed bottom-4 right-4 flex flex-col gap-2">
    <button
      @click="openSidebar('schema')"
      class="p-3 rounded-full shadow bg-sky-600 text-white"
    >Schema</button>
    <button
      @click="openSidebar('cypher')"
      class="p-3 rounded-full shadow bg-sky-600 text-white"
    >Cypher</button>
  </div>

  <!-- desktop show button when hidden -->
  <button
    v-if="!isMobile && !sidebarVisible"
    @click="sidebarVisible = true"
    class="fixed top-1/2 right-0 p-2 rounded-l shadow bg-sky-600 text-white"
  >
    &lt;
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

const schemaWidth   = ref(350); // px
const showSidebar   = ref(false);    // mobile overlay
const sidebarVisible = ref(true);    // desktop visibility
const sidebarTab     = ref('schema');
const isMobile    = ref(window.innerWidth < 640);
const SCHEMA_MIN_WIDTH = 240; // px

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
  return Math.max(16, half); // keep at least 16 px
});

const query = ref('');
const messages = ref(/** @type {{role:string,content:string}[]} */([]));
const loading = ref(false);
// remember last‑chosen agent across page refreshes
const useRemote = ref(localStorage.getItem('useRemote') === 'true');
const inputAtBottom = ref(false);

const apiBase = computed(() => (useRemote.value ? '/api/remote' : '/api/local'));

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
  inputAtBottom.value = true;
  query.value = '';
  loading.value = true;

  const endpoint = `${apiBase.value}/ask`;

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
  const endpoint = `${apiBase.value}/history`;
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
  const endpoint = `${apiBase.value}/clear`;
  try {
    await axios.post(endpoint);
  } catch {}
}

onMounted(loadHistory);
watch(useRemote, val => {
  localStorage.setItem('useRemote', val);
  loadHistory();
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

section,
aside {
  min-height: 0; /* let the grid cells shrink properly */
}

/* ensure the drag handle stretches full height */
.cursor-col-resize {
  min-height: 100%;
}

/* hide body scrollbars when mobile overlay is open */
body.overlay-open {
  overflow: hidden;
}
</style>