<template>
  <div class="d-md-flex gap-2">
    <button type="button" class="btn" :class="btnClass" @click="this.show()"
            aria-expanded="false" :aria-controls="id" :disabled="isVisible">
      <slot name="label"></slot>
    </button>
    <div class="flex-grow-1" :class="isVisible ? '': 'visually-hidden'" :id="id">
      <div class="card">
        <div class="card-body d-flex p-1 align-items-center">
          <button type="button" class="btn btn-sm btn-outline-dark" aria-label="Cancel"
                  @click="this.hide()">
            Cancel
          </button>
          <span class="text-cta flex-grow-1 text-center">
            <slot name="confirm">
              Please confirm that you want to continue.
            </slot>
          </span>
          <button type="button" class="btn btn-sm btn-cta flex-grow-1" @click="callback">
            Confirm
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "ConfirmButton",
  props: {
    callback: {
      type: Function,
      required: true
    },
    btnClass: {
      default: "btn-outline",
      type: String
    },
    id: {
      type: String,
      default: `confirm-${crypto.randomUUID()}`
    }
  },
  data() {
    return {
      isVisible: false
    }
  },
  methods: {
    show() {
      this.isVisible = true;
    },
    hide() {
      this.isVisible = false;
    }
  }
}
</script>

<style scoped>

</style>