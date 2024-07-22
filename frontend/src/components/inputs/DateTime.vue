<template>
  <BaseInput :label="label" :args="args" :vertical="vertical" :required="required">
    <template v-slot:field>
      <input class="form-control" type="datetime-local"
             :value="value"
             @input="onInput"
             v-bind="args"/>
    </template>
  </BaseInput>
</template>

<script>
import BaseInput from "@/components/layout/BaseInput.vue";

export default {
  name: "DateTime",
  components: {BaseInput},
  props: ["label", "modelValue", "args", "vertical", "required"],
  computed: {
    value() {
      return this.modelValue && this.convertToDateTimeLocalString(this.modelValue);
    }
  },
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
    },
    convertToDateTimeLocalString(date) {
      if (!(date instanceof Date)) {
        date = new Date(date)
      }

      return date.toISOString().substring(0, 16);
    }
  },
};
</script>
