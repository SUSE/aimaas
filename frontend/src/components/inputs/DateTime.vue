<template>
  <BaseInput :label="label" :args="args" :vertical="vertical" :required="required">
    <template v-slot:field>
      <input class="form-control" type="datetime-local"
             :value="modelValue && convertToDateTimeLocalString(modelValue)"
             @input="onInput"
             v-bind="args"/>
    </template>
  </BaseInput>
</template>

<script>
import BaseInput from "@/components/layout/BaseInput";

export default {
  name: "DateTime",
  components: {BaseInput},
  props: ["label", "modelValue", "args", "vertical", "required"],
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
    },
    convertToDateTimeLocalString(date) {
      if (!(date instanceof Date)) {
        date = new Date(date)
      }

      const year = date.getFullYear();
      const month = (date.getMonth() + 1).toString().padStart(2, "0");
      const day = date.getDate().toString().padStart(2, "0");
      const hours = date.getHours().toString().padStart(2, "0");
      const minutes = date.getMinutes().toString().padStart(2, "0");

      return `${year}-${month}-${day}T${hours}:${minutes}:00`;
    }
  },
};
</script>