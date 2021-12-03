<template>
  <label v-if="label">
    {{ label }}
  </label>
  <input
    class="form-control"
    type="number"
    :value="modelValue"
    @input="onInput"
  />
</template>

<script>
export default {
  name: "FloatInput",
  props: ["label", "modelValue"],
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
    },
  },
};
</script>