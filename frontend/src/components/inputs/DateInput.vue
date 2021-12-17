<template>
  <BaseInput :label="label" :args="args" :vertical="vertical">
    <template v-slot:field>
      <input class="form-control" type="date" :value="modelValue" @input="onInput" v-bind="args"/>
    </template>
  </BaseInput>

</template>

<script>
import BaseInput from "@/components/layout/BaseInput";

export default {
  name: "DateInput",
  components: {BaseInput},
  props: ["label", "modelValue", "args", "vertical"],
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
    },
  },
};
</script>