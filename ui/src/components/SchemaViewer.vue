<template>
  <div class="p-4 text-sm overflow-y-auto h-full flex flex-col gap-4">
    <h1 class="text-lg font-semibold">Neo4j Schema</h1>
    <div>
      <h2 class="font-semibold mb-2">Node Labels</h2>
      <div v-for="(props, label) in schema.NodeTypes" :key="label" class="mb-3">
        <h3 class="font-medium">{{ label }}</h3>
        <ul class="list-disc ml-4">
          <li v-for="(type, prop) in props" :key="prop">
            <span class="font-mono">{{ prop }}</span>: {{ type }}
          </li>
        </ul>
      </div>
    </div>

    <div>
      <h2 class="font-semibold mb-2 mt-4">Relationship Types</h2>
      <div
        v-for="(info, rel) in schema.RelationshipTypes"
        :key="rel"
        class="mb-3"
      >
        <h3 class="font-medium">{{ rel }}</h3>
        <p class="text-xs text-gray-500">
          ({{ info._endpoints?.[0] }}) -[{{ rel }}]-> ({{ info._endpoints?.[1] }})
        </p>
        <ul
          v-if="Object.keys(filterProps(info)).length"
          class="list-disc ml-4"
        >
          <li v-for="(type, prop) in filterProps(info)" :key="prop">
            <span class="font-mono">{{ prop }}</span>: {{ type }}
          </li>
        </ul>
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
