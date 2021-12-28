<template>
  <BaseInput :label="label" :args="args" :vertical="vertical" :required="required">
    <template v-slot:field>
      <input class="form-control" type="text" :value="modelValue" @input="onInput" v-bind="args"
             :list="datalistId"/>
      <datalist :id="datalistId">
      <slot name="datalist" />
    </datalist>
    </template>
    <template v-slot:helptext>
      <slot name="helptext"/>
    </template>
  </BaseInput>
</template>

<script>
import BaseInput from "@/components/layout/BaseInput";

export default {
  name: "TextInput",
  components: {BaseInput},
  props: ["label", "modelValue", "args", "vertical", "required"],
  emits: ["update:modelValue"],
  computed: {
    datalistId() {
      return `dl-${this.args.id}`;
    },
  },
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
    },
  },
};
</script>