<template>
  <div :class="classes" data-bs-toggle="tooltip" :title="args.tooltip">
    <label :for="args.id" :class="labelClass" v-if="label">
      <slot name="label">
        {{ label }}
        <sup
          v-if="required"
          class="text-danger"
          data-bs-toggle="tooltip"
          title="This value is required"
          >*</sup
        >
      </slot>
    </label>
    <div :class="columns">
      <slot name="field" />
      <div
        class="d-flex flex-row-reverse justify-content-between align-items-center px-1"
      >
        <div class="text-muted">
          <small>
            <slot name="helptext" />
          </small>
        </div>
        <slot name="bottom-left" />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "BaseInput",
  props: {
    label: {
      type: String,
      default: "",
    },
    args: {
      type: Object,
      default: () => {},
    },
    withoutOffset: {
      type: Boolean,
      default: false,
    },
    vertical: {
      type: Boolean,
      default: false,
    },
    required: {
      type: Boolean,
      default: false,
    },
  },
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
      return "form-label";
    },
    columns() {
      if (this.vertical) {
        return "";
      }
      if (this.withoutOffset) {
        return "col-lg-12";
      }
      return "col-lg-10";
    },
  },
};
</script>
