<template>
  <BaseInput :label="label" :args="args" :vertical="vertical" :required="required">
    <template v-slot:field>
      <textarea class="form-control" type="text" :value="modelValue" @input="onInput"
                v-bind="args"/>
    </template>
    <template v-slot:helptext>
      <slot name="helptext"/>
    </template>
  </BaseInput>
</template>

<script>
import BaseInput from "@/components/layout/BaseInput";

export default {
  name: "TextareaInput",
  components: {BaseInput},
  props: ["label", "modelValue", "args", "vertical", "required"],
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
    },
  },
};
</script>
