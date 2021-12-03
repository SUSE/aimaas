<template>
  <label :for="args.id" v-if="label" class="form-label">
    {{ label }}
  </label>
  <textarea
    class="form-control"
    type="text"
    :value="modelValue"
    @input="onInput"
    v-bind="args"
  />
</template>

<script>
export default {
  name: "Textarea",
  props: ["label", "modelValue", "args"],
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
    },
  },
};
</script>