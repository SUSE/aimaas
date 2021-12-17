<template>
  <div :class="classes" data-bs-toggle="tooltip"
       :title="args.tooltip">
    <label :for="args.id" :class="labelClass" v-if="label">
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
  props: ["label", "args", "withoutOffset", "vertical"],
  computed: {
    classes() {
      let cls = "mb-1 pb-1 border-bottom border-light";
      if (!this.vertical) {
        cls += " row";
        if (!this.withoutOffset) {
          cls += " justify-content-end";
        }
      } else {
        cls += "";
      }
      return cls;
    },
    labelClass() {
      if (!this.vertical) {
        return "col-form-label col-lg-2";
      }
      return "form-label"
    },
    columns() {
      if (this.vertical) {
        return "";
      }
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