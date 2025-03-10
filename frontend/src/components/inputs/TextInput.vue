<template>
  <BaseInput
    :label="label"
    :args="args"
    :vertical="vertical"
    :required="required"
  >
    <template v-slot:field>
      <input
        class="form-control"
        type="text"
        v-model.trim="modelValue"
        v-bind="args"
        :list="datalistId"
      />
      <datalist :id="datalistId">
        <slot name="datalist" />
      </datalist>
    </template>
    <template v-slot:helptext>
      <slot name="helptext" />
    </template>
  </BaseInput>
</template>

<script setup>
import BaseInput from "@/components/layout/BaseInput.vue";
import { computed } from "vue";

const modelValue = defineModel({ required: true });

const props = defineProps([
  "label",
  "string",
  "args",
  "vertical",
  "boolean",
  "required",
]);

const datalistId = computed(() => {
  return `dl-${props.args.id}`;
});
</script>
