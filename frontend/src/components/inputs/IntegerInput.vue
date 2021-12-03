<template>
  <label :for="args.id" v-if="label" class="form-label">
    {{ label }}
  </label>
  <input
    class="form-control"
    type="number"
    step="1"
    :value="modelValue"
    @input="onInput"
    v-bind="args"
  />
</template>

<script>
export default {
  name: "IntegerInput",
  props: ["label", "modelValue", "args"],
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
    },
  },
};
</script>