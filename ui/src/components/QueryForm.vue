<template>
  <Card class="shadow-2 mb-4">
    <template #title>
      <div class="flex justify-between items-center">
        <span class="text-primary font-medium flex items-center gap-2">
          Ask AI <i class="pi pi-android"></i>
        </span>

        <div class="flex items-center gap-4">
          <!-- Local agent -->
          <div
            class="flex items-center gap-2"
            v-tooltip="'Runs the in‑process schema‑retriever agent (no remote calls).'"
          >
            <RadioButton v-model="selectedApi" inputId="local" value="local" />
            <label for="local" class="font-medium text-sm cursor-pointer"
              >Local Agent</label
            >
          </div>

          <!-- Remote (Assistant) agent -->
          <div
            class="flex items-center gap-2"
            v-tooltip="'Sends the question to the OpenAI Assistant you configured remotely.'"
          >
            <RadioButton v-model="selectedApi" inputId="remote" value="remote" />
            <label for="remote" class="font-medium text-sm cursor-pointer"
              >Remote Agent</label
            >
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
            placeholder="Ask a natural‑language question to generate a Cypher query…"
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
const emit = defineEmits(['update:modelValue', 'submit', 'update:useRemote']);

const selectedApi = ref('local');     // default: local agent

watch(selectedApi, (val) => emit('update:useRemote', val === 'remote'));

const localValue = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
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