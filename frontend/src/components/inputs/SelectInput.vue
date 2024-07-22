<template>
  <BaseInput :label="label" :args="args" :vertical="vertical" :required="required">
    <template v-slot:field>
      <select @change="onInput" class="form-control" v-bind="args" :value="modelValue">
        <option v-for="opt in options" :key="opt?.value" :value="opt?.value">
          {{ opt?.text || opt?.value }}
        </option>
      </select>
    </template>
  </BaseInput>
</template>

<script>
import BaseInput from "@/components/layout/BaseInput.vue";

export default {
  name: "SelectInput",
  components: {BaseInput},
  props: ["label", "modelValue", "args", "options", "vertical", "required"],
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
    },
  },
};
</script>
