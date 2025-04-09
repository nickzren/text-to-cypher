<template>
    <Card class="shadow-2 mt-4">
      <template #title>
        <div class="flex justify-between items-center">
          <span class="text-primary font-medium flex items-center gap-2">
            AI <i class="pi pi-android"></i> Response
          </span>
          <Button 
            icon="pi pi-copy"
            label="Copy"
            severity="secondary"
            text
            rounded
            @click="copyToClipboard"
            v-tooltip="'Copy to Clipboard'"
          />
        </div>
      </template>
  
      <template #content>
        <pre class="bg-gray-100 text-gray-800 text-sm p-3 rounded overflow-x-auto font-mono whitespace-pre-wrap leading-snug"><code>{{ cleanedResponse }}</code></pre>
      </template>
    </Card>
  </template>
  
  <script setup>
  import { computed } from 'vue'
  import { useToast } from 'primevue/usetoast'
  import Card from 'primevue/card'
  import Button from 'primevue/button'
  
  const props = defineProps({
    response: String,
  })
  
  const toast = useToast()
  
  const cleanedResponse = computed(() => {
    return props.response
      ?.replace(/^```(?:cypher)?/i, '')
      .replace(/```$/, '')
      .trim() || ''
  })
  
  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(cleanedResponse.value)
      toast.add({ severity: 'success', summary: 'Copied', detail: 'Cypher query copied to clipboard.', life: 2000 })
    } catch (err) {
      toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to copy.', life: 2000 })
    }
  }
  </script>