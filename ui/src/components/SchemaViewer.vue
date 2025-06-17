<template>
  <div class="p-6 text-sm overflow-y-auto h-full">
    <h1 class="text-xl font-semibold text-gray-800 mb-6">Neo4j Schema</h1>
    
    <!-- Node Labels Section -->
    <div class="mb-8">
      <div class="flex items-center gap-2 mb-4">
        <div class="w-1 h-5 bg-sky-500 rounded-full"></div>
        <h2 class="text-base font-semibold text-gray-700">Node Labels</h2>
      </div>
      
      <div class="space-y-3">
        <div 
          v-for="(props, label) in schema.NodeTypes" 
          :key="label"
          class="bg-white rounded-lg p-4 shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
        >
          <h3 class="font-medium text-gray-800 mb-2 flex items-center gap-2">
            <i class="pi pi-circle-fill text-xs text-sky-500"></i>
            {{ label }}
          </h3>
          <div v-if="Object.keys(props).length" class="ml-6 space-y-1">
            <div 
              v-for="(type, prop) in props" 
              :key="prop"
              class="flex items-center text-xs text-gray-600"
            >
              <span class="font-mono text-gray-500">{{ prop }}</span>
              <span class="mx-2 text-gray-400">:</span>
              <span class="text-gray-700">{{ type }}</span>
            </div>
          </div>
          <div v-else class="ml-6 text-xs text-gray-400 italic">
            No properties defined
          </div>
        </div>
      </div>
    </div>

    <!-- Relationship Types Section -->
    <div>
      <div class="flex items-center gap-2 mb-4">
        <div class="w-1 h-5 bg-emerald-500 rounded-full"></div>
        <h2 class="text-base font-semibold text-gray-700">Relationship Types</h2>
      </div>
      
      <div class="space-y-3">
        <div
          v-for="(info, rel) in schema.RelationshipTypes"
          :key="rel"
          class="bg-white rounded-lg p-4 shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
        >
          <h3 class="font-medium text-gray-800 mb-1">{{ rel }}</h3>
          <p class="text-xs text-gray-500 mb-2 font-mono">
            ({{ info._endpoints?.[0] }}) -[{{ rel }}]-> ({{ info._endpoints?.[1] }})
          </p>
          <div
            v-if="Object.keys(filterProps(info)).length"
            class="ml-6 space-y-1"
          >
            <div 
              v-for="(type, prop) in filterProps(info)" 
              :key="prop"
              class="flex items-center text-xs text-gray-600"
            >
              <span class="font-mono text-gray-500">{{ prop }}</span>
              <span class="mx-2 text-gray-400">:</span>
              <span class="text-gray-700">{{ type }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const schema = ref({ NodeTypes: {}, RelationshipTypes: {} })

function filterProps(info) {
  const copy = { ...info }
  delete copy._endpoints
  return copy
}

onMounted(async () => {
  try {
    const res = await axios.get('/api/schema')
    schema.value = res.data
  } catch (err) {
    console.error('Failed to load schema', err)
  }
})
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