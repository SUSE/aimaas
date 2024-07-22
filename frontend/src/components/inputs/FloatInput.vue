<template>
  <BaseInput :label="label" :args="args" :vertical="vertical" :required="required">
    <template v-slot:field>
      <input class="form-control" type="number" :value="modelValue" @input="onInput" v-bind="args"/>
    </template>
  </BaseInput>
</template>

<script>
import BaseInput from "@/components/layout/BaseInput.vue";

export default {
  name: "FloatInput",
  props: ["label", "modelValue", "args", "vertical", "required"],
  components: {BaseInput},
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
    },
  },
};
</script>
