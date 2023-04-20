<template>
  <BaseInput label="" :args="args" :without-offset="withoutOffset" :vertical="vertical"
             :required="required">
    <template v-slot:field>
      <div class="d-grid gap-2">
        <input class="btn-check" type="checkbox" v-model="this.checked" :true-value="true"
               :false-value="false" autocomplete="off" v-bind="uniqueArgs"
               @change="this.$emit('update:modelValue', this.checked)" />
        <label class="btn" :class="this.checked? 'btn-primary' : 'btn-light'"
               :for="uniqueArgs.id">
          {{ label || '&nbsp;'}}
        </label>
      </div>
    </template>
    <template v-slot:helptext>
      <slot name="helptext"/>
    </template>
  </BaseInput>
</template>

<script>
import BaseInput from "@/components/layout/BaseInput";

export default {
  name: "Checkbox",
  components: {BaseInput},
  props: ["label", "modelValue", "args", "withoutOffset", "vertical", "required"],
  data() {
    return {
      checked: false,
    };
  },
  computed: {
    uniqueArgs() {
      return {
        id: `checkbox-${this.$.uid}-${this.args.id}`,
        label: this.args.label
      }
    }
  },
  methods: {
    onInput() {
      this.checked = !this.checked;
      this.$emit("update:modelValue", this.checked);
    },
  },
  watch: {
    modelValue: {
      handler(value) {
        this.checked = value
      },
      immediate: true,
      deep: true
    }
  }
};
</script>
