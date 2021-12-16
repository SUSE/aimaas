<template>
  <div class="row mb-1 pb-1 border-bottom border-light" :class="justify" data-bs-toggle="tooltip"
       :title="args.tooltip">
    <label :for="args.id" class="col-form-label col-lg-2" v-if="label">
      <slot name="label">
        {{ label }}
      </slot>
    </label>
    <div :class="columns">
      <slot name="field"/>
      <div class="text-muted text-end">
        <small>
          <slot name="helptext"/>
        </small>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "BaseInput",
  props: ["label", "args", "withoutOffset"],
  computed: {
    justify() {
      if (this.withoutOffset) {
        return "";
      }
      return "justify-content-end";
    },
    columns() {
      if (this.withoutOffset) {
        return "col-lg-12";
      }
      return "col-lg-10";
    }
  }
}
</script>

<style scoped>

</style>