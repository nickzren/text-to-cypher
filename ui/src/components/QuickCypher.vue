<template>
  <div class="p-6 text-sm overflow-y-auto h-full">
    <h1 class="text-xl font-semibold text-gray-800 mb-6">Quick Cypher</h1>
    
    <div class="space-y-6">
      <div
        v-for="(category, catIdx) in categories"
        :key="catIdx"
      >
        <h2 class="text-sm font-medium text-gray-600 mb-3 flex items-center gap-2">
          <i :class="category.icon" class="text-xs"></i>
          {{ category.name }}
        </h2>
        
        <div class="space-y-3">
          <div
            v-for="(item, idx) in category.scripts"
            :key="idx"
            class="bg-white rounded-lg p-4 shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
          >
            <p class="text-sm font-medium text-gray-700 mb-2">
              {{ item.desc }}
            </p>
            <div class="bg-gray-50 rounded p-3 group relative">
              <pre class="text-xs text-gray-700 font-mono whitespace-pre-wrap">{{ item.query }}</pre>
              <div class="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  @click="emit('run-query', item.query)"
                  class="p-1.5 bg-white rounded shadow-sm text-gray-500 hover:text-gray-700 hover:shadow transition-all"
                  title="Open in Neo4j Browser"
                >
                  <i class="pi pi-play text-xs"></i>
                </button>
                <button
                  @click="copyToClipboard(item.query)"
                  class="p-1.5 bg-white rounded shadow-sm text-gray-500 hover:text-gray-700 hover:shadow transition-all"
                  title="Copy to Clipboard"
                >
                  <i class="pi pi-copy text-xs"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useToast } from 'primevue/usetoast'

const emit = defineEmits(['run-query'])
const toast = useToast()

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    toast.add({ severity: 'success', summary: 'Copied', life: 1500 })
  }).catch(() => {
    toast.add({ severity: 'error', summary: 'Copy failed', life: 1500 })
  })
}

const categories = [
  {
    name: 'Schema Exploration',
    icon: 'pi pi-sitemap',
    scripts: [
      {
        query: 'CALL db.schema.visualization',
        desc: 'Visualize the database schema'
      },
      {
        query: 'MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC',
        desc: 'Count nodes by label'
      },
      {
        query: 'MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY count DESC',
        desc: 'Count relationships by type'
      }
    ]
  },
  {
    name: 'Sample Queries',
    icon: 'pi pi-search',
    scripts: [
      {
        query: 'MATCH (n) RETURN n LIMIT 25',
        desc: 'Return first 25 nodes'
      },
      {
        query: 'MATCH p=()-[r]->() RETURN p LIMIT 25',
        desc: 'Return first 25 relationships'
      }
    ]
  }
]
</script>

<style scoped>
/* Smooth scrollbar styling */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: #f3f4f6;
}

::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}
</style>