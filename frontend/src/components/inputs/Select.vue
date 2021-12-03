<template>
  <label :for="args.id" v-if="label" class="form-label">
    {{ label }}
  </label>
  <select @change="onInput" class="form-control" v-bind="args">
    <option v-for="opt in options" :key="opt.value" :value="opt.value">
      {{ opt.text || opt.value }}
    </option>
  </select>
</template>

<script>
export default {
  name: "Select",
  props: ["label", "modelValue", "args", "options"],
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
    },
  },
};
</script>