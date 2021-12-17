<template>
  <BaseInput :label="label" :args="args" :vertical="vertical">
    <template v-slot:field>
      <input class="form-control" type="number" :value="modelValue" @input="onInput" v-bind="args"/>
    </template>
  </BaseInput>
</template>

<script>
import BaseInput from "@/components/layout/BaseInput";

export default {
  name: "FloatInput",
  props: ["label", "modelValue", "args", "vertical"],
  components: {BaseInput},
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
    },
  },
};
</script>