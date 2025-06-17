<!-- ui/src/components/QueryForm.vue -->
<template>
  <div class="relative">
    <!-- Main input with integrated controls -->
    <div class="relative flex items-center">
      <Textarea
        v-model="localValue"
        :rows="3"
        :autoResize="true"
        placeholder="Ask a natural‑language question to generate a Cypher query…"
        class="w-full pr-32 text-sm query-input"
        @keydown="handleKeydown"
      />
      
      <!-- Controls inside textarea -->
      <div class="absolute bottom-2 right-2 flex items-center gap-1">
        <!-- LLM selector - PrimeVue Dropdown -->
        <Dropdown
          v-model="selectedLLM"
          :options="llmOptions"
          optionLabel="label"
          optionValue="value"
          class="llm-dropdown"
          :pt="{
            root: { class: 'h-7 flex items-center text-xs' },
            input: { class: 'py-0 pl-2 pr-0 text-xs bg-transparent border-0 text-gray-600 flex items-center h-full' },
            trigger: { class: 'w-4 flex items-center justify-center pl-0' },
            panel: { class: 'text-sm' },
            item: { class: 'py-1.5 px-3 text-sm' }
          }"
        />
        
        <!-- Submit button - PrimeVue Button -->
        <Button
          @click="submitForm"
          :disabled="!localValue.trim() || loading"
          :loading="loading"
          icon="pi pi-arrow-up"
          severity="info"
          size="small"
          class="submit-button"
          :pt="{
            root: { class: 'w-7 h-7' },
            icon: { class: 'text-xs' }
          }"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import Textarea from 'primevue/textarea';
import Button from 'primevue/button';
import Dropdown from 'primevue/dropdown';

const props = defineProps({
  modelValue: String,
  loading: Boolean,
  selectedProvider: String,
})
const emit = defineEmits(['update:modelValue', 'submit', 'update:selectedProvider']);

const llmOptions = [
  { label: 'o4-mini', value: 'openai' },
  { label: 'OpenAI Assistant', value: 'assistant' },
  { label: 'Gemini 2.5 Pro', value: 'google' }
];

const selectedLLM = computed({
  get: () => props.selectedProvider,
  set: (val) => emit('update:selectedProvider', val),
})

const localValue = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
});

function submitForm() {
  if (localValue.value.trim() && !props.loading) {
    emit('submit');
  }
}

function handleKeydown(event) {
  // Submit on Enter (without Shift)
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    submitForm();
  }
}
</script>

<style scoped>
/* Clean textarea styling */
:deep(.query-input.p-inputtextarea) {
  max-height: 10rem;
  overflow-y: auto;
  padding-right: 8rem;
  font-size: 0.875rem;
  line-height: 1.5;
  background-color: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  min-height: 5rem; /* Ensure minimum height for 3 lines */
}

:deep(.query-input.p-inputtextarea:focus) {
  background-color: white;
  border-color: #d1d5db;
  outline: none;
}

/* Override PrimeVue button padding to make it more square */
:deep(.submit-button.p-button) {
  padding: 0;
  min-width: 1.75rem;
  min-height: 1.75rem;
}

:deep(.submit-button .p-button-icon) {
  margin: 0;
}

/* Make dropdown look more subtle and integrated with no spacing */
:deep(.llm-dropdown) {
  min-width: auto;
  background-color: transparent;
  border: none;
  box-shadow: none;
}

:deep(.llm-dropdown:hover) {
  background-color: #f3f4f6;
  border-radius: 0.25rem;
}

:deep(.llm-dropdown:not(.p-disabled).p-focus) {
  box-shadow: none;
  background-color: #f3f4f6;
}

:deep(.llm-dropdown .p-dropdown-trigger) {
  background: transparent;
  padding: 0;
  margin-left: -2px; /* Pull trigger closer to text */
}

:deep(.llm-dropdown .p-dropdown-label) {
  font-weight: 500;
  display: flex;
  align-items: center;
  height: 100%;
  line-height: 1;
  padding-right: 0;
}

/* Ensure proper vertical alignment */
:deep(.llm-dropdown .p-inputtext) {
  display: flex;
  align-items: center;
}

/* Override the dropdown icon spacing */
:deep(.llm-dropdown .p-icon) {
  width: 0.75rem;
  height: 0.75rem;
}
</style>