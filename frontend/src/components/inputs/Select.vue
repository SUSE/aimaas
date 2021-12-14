<template>
  <BaseInput :label="label" :args="args">
    <template v-slot:field>
      <select @change="onInput" class="form-control" v-bind="args">
        <option v-for="opt in options" :key="opt.value" :value="opt.value">
          {{ opt.text || opt.value }}
        </option>
      </select>
    </template>
  </BaseInput>
</template>

<script>
import BaseInput from "@/components/layout/BaseInput";

export default {
  name: "Select",
  components: {BaseInput},
  props: ["label", "modelValue", "args", "options"],
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
    },
  },
};
</script>