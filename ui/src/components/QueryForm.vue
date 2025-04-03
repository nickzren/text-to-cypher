<!-- ui/src/components/QueryForm.vue -->
<template>
    <Card class="shadow-2 mb-4">
        <template #title>
            <span class="text-primary font-medium flex items-center gap-2">
            Ask AI <i class="pi pi-android"></i>
            </span>
        </template>

        <template #content>
            <form @submit.prevent="submitForm" class="p-fluid">
            <div class="field mb-3">
                <Textarea
                v-model="localValue"
                rows="5"
                autoResize
                placeholder="Ask a natural language question to generate a Cypher query..."
                class="w-full"
                />
            </div>
            <div class="field text-right">
                <Button
                type="submit"
                label="Submit Query"
                icon="pi pi-send"
                severity="info"
                :loading="loading"
                :disabled="!localValue.trim()"
                />
            </div>
            </form>
        </template>
    </Card>
  </template>
  
  <script setup>
  import { computed } from 'vue';
  import Textarea from 'primevue/textarea';
  import Button from 'primevue/button';
  import Card from 'primevue/card';
  
  const props = defineProps({
    modelValue: String,
    loading: Boolean,
  });
  const emit = defineEmits(['update:modelValue', 'submit']);
  
  const localValue = computed({
    get: () => props.modelValue,
    set: (val) => emit('update:modelValue', val),
  });
  
  function submitForm() {
    emit('submit');
  }
  </script>