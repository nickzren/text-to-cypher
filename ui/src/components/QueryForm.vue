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
        class="w-full pr-24 text-sm query-input"
        @keydown="handleKeydown"
      />
      
      <!-- Controls inside textarea -->
      <div class="absolute bottom-2 right-2 flex items-center gap-1">
        <!-- Agent selector - PrimeVue Dropdown -->
        <Dropdown
          v-model="selectedApi"
          :options="apiOptions"
          optionLabel="label"
          optionValue="value"
          class="agent-dropdown"
          :pt="{
            root: { class: 'h-7 flex items-center text-xs' },
            input: { class: 'py-0 px-2 pr-6 text-xs bg-transparent border-0 text-gray-600 flex items-center h-full' },
            trigger: { class: 'w-5 flex items-center' },
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
  useRemote: Boolean,
})
const emit = defineEmits(['update:modelValue', 'submit', 'update:useRemote']);

const apiOptions = [
  { label: 'Local', value: 'local' },
  { label: 'Remote', value: 'remote' }
];

const selectedApi = computed({
  get: () => (props.useRemote ? 'remote' : 'local'),
  set: (val) => emit('update:useRemote', val === 'remote'),
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
  padding-right: 6rem;
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

/* Make dropdown look more subtle and integrated */
:deep(.agent-dropdown) {
  min-width: auto;
  background-color: transparent;
  border: none;
  box-shadow: none;
}

:deep(.agent-dropdown:hover) {
  background-color: #f3f4f6;
  border-radius: 0.25rem;
}

:deep(.agent-dropdown:not(.p-disabled).p-focus) {
  box-shadow: none;
  background-color: #f3f4f6;
}

:deep(.agent-dropdown .p-dropdown-trigger) {
  background: transparent;
}

:deep(.agent-dropdown .p-dropdown-label) {
  font-weight: 500;
  display: flex;
  align-items: center;
  height: 100%;
  line-height: 1;
}

/* Ensure proper vertical alignment */
:deep(.agent-dropdown .p-inputtext) {
  display: flex;
  align-items: center;
}
</style>