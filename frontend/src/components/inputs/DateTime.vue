<template>
  <label :for="args.id" v-if="label" class="form-label">
    {{ label }}
  </label>
  <input
    class="form-control"
    type="datetime-local"
    :value="modelValue"
    @input="onInput"
    v-bind="args"
  />
</template>

<script>
export default {
  name: "DateTime",
  props: ["label", "modelValue", "args"],
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
    },
  },
};
</script>