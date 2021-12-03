<template>
  <input
    class="form-check-input"
    type="checkbox"
    :checked="this.checked"
    @input="onInput"
    v-bind="args"
  />
  <label :for="args.id" v-if="label" class="form-check-label ms-1">
    {{ label }}
  </label>
</template>

<script>
export default {
  name: "Checkbox",
  props: ["label", "modelValue", "args"],
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