<!-- ui/src/components/QueryForm.vue -->
<template>
    <Card class="shadow-2 mb-4">
      <template #title>
        <div class="flex justify-between items-center">
            <span class="text-primary font-medium flex items-center gap-2">
                Ask AI <i class="pi pi-android"></i>
            </span>
            <div class="flex items-center gap-4">
                <div class="flex items-center gap-2" v-tooltip="'Uses a standard OpenAI API call where schema validation and instructions are defined explicitly in the prompt.'">
                    <RadioButton v-model="selectedApi" inputId="direct" value="direct" />
                    <label for="direct" class="font-medium text-sm cursor-pointer">Direct Model</label>
                </div>
                <div class="flex items-center gap-2" v-tooltip="'Uses a pre-configured OpenAI Assistant with built-in schema validation and structured instructions stored directly in the OpenAI platform.'">
                    <RadioButton v-model="selectedApi" inputId="assistant" value="assistant" />
                    <label for="assistant" class="font-medium text-sm cursor-pointer">Custom Assistant</label>
                </div>
            </div>
        </div>
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
  import { computed, ref, watch } from 'vue';
  import Textarea from 'primevue/textarea';
  import Button from 'primevue/button';
  import Card from 'primevue/card';
  import RadioButton from 'primevue/radiobutton';
  import Tooltip from 'primevue/tooltip';
  
  const props = defineProps({
    modelValue: String,
    loading: Boolean,
  });
  
  const emit = defineEmits(['update:modelValue', 'submit', 'update:useAssistant']);
  
  const selectedApi = ref('direct'); // Default API selection is Direct Model
  
  watch(selectedApi, (newValue) => {
    emit('update:useAssistant', newValue === 'assistant');
  });
  
  const localValue = computed({
    get: () => props.modelValue,
    set: (val) => emit('update:modelValue', val),
  });
  
  function submitForm() {
    emit('submit');
  }
  </script>
  
  <style scoped>
  .cursor-pointer {
    cursor: pointer;
  }
  </style>