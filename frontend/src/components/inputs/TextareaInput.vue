<template>
  <BaseInput :label="label" :args="args" :vertical="vertical" :required="required">
    <template v-slot:field>
      <textarea
        v-model.trim="modelValue"
        @input="onInput"
        v-bind="args"
        type="text"
        class="form-control"
      />
    </template>
    <template v-slot:helptext>
      <slot name="helptext" />
    </template>
    <template v-slot:bottom-left v-if="max_characters">
      <small :class="`counter ${counterColorClass}`"
        >{{ modelValue?.length ?? 0 }}/{{ max_characters }}</small
      >
    </template>
  </BaseInput>
</template>

<script setup>
import BaseInput from "@/components/layout/BaseInput.vue";
import { computed } from "vue";

const modelValue = defineModel({ required: true, default: "" });
const props = defineProps([
  "label",
  "args",
  "vertical",
  "required",
  "max_characters",
]);

const counterColorClass = computed(() => {
  if (
    modelValue.value &&
    props.max_characters &&
    modelValue.value.length > props.max_characters
  ) {
    return "text-danger";
  }
  return "text-muted";
});
</script>

<style lang="css" scoped>
.counter {
  font-size: xx-small;
}
</style>
