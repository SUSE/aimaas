<template>
  <label v-if="label">
    {{ label }}
  </label>
  <input
    class="form-check-input"
    type="checkbox"
    :checked="this.checked"
    @input="onInput"
  />
</template>

<script>
export default {
  name: "Checkbox",
  props: ["label", "modelValue"],
  data() {
    return {
      checked: null,
    };
  },
  created() {
    this.checked = this.modelValue;
  },
  methods: {
    onInput() {
      this.checked = !this.checked;
      this.$emit("update:modelValue", this.checked);
    },
  },
};
</script>