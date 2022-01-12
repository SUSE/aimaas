<template>
  <BaseInput :label="label" :args="args" :vertical="vertical" :required="required">
    <template v-slot:field>
      <div class="input-group dropstart">
        <input type="text" class="form-control" aria-label="Parent group"
               :value="selectedText" disabled>
        <button class="btn btn-outline-secondary dropdown-toggle" type="button"
                data-bs-toggle="dropdown" aria-expanded="false" :disabled="disabled">
          Select
        </button>
        <div class="dropdown-menu">
          <input type="text" class="form-control" placeholder="Filter" v-model="filterString"
                 :disabled="disabled"/>
          <div class="dropdown-divider"/>
          <template v-if="matchingOptions.length > 0">
            <button class="dropdown-item" v-for="option of matchingOptions" :key="option.value"
                    @click="$emit('update:modelValue', option.value)" :disabled="disabled">
              {{ option?.text || option.value }}
            </button>
          </template>
          <div v-else class="alert alert-info">
            No matching options.
          </div>
        </div>
      </div>
    </template>
  </BaseInput>
</template>

<script>
import BaseInput from "@/components/layout/BaseInput";

export default {
  name: "DropdownSelect",
  components: {BaseInput},
  props: ["label", "modelValue", "args", "vertical", "required", "options", "disabled"],
  emits: ["update:modelValue"],
  data() {
    return {
      filterString: ""
    }
  },
  computed: {
    matchingOptions() {
      if (this.filterString.length) {
        return this.options.filter(x => x.text.toLowerCase().includes(this.filterString.toLowerCase()));
      }
      return this.options;
    },
    selectedText() {
      return this.options.filter(x => x.value === this.modelValue).map(x => x.text || x.value)[0];
    }
  }
}
</script>

<style scoped>

</style>