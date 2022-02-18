<template>
  <div class="gap-2" :class="wrapperClass">
    <button type="button" class="btn" :class="btnClass" @click="this.show()"
            aria-expanded="false" :aria-controls="id" :disabled="isVisible">
      <slot name="label"></slot>
    </button>
    <div :class="hiddenClass" :id="id">
      <div class="card">
        <div class="card-body d-flex p-1 gap-2" :class="cardClass">
          <button type="button" class="btn btn-sm btn-outline-dark" @click="this.hide()"
                  :class="reverse ? 'order-last' : ''" aria-label="Cancel">
            Cancel
          </button>
          <span class="text-cta flex-grow-1 text-center">
            <slot name="confirm">
              Please confirm that you want to continue.
            </slot>
          </span>
          <button type="button" class="btn btn-sm btn-cta flex-grow-1" @click="callback"
                  :class="reverse ? 'order-first': ''" :value="value">
            Confirm
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import {randomUUID} from "@/utils";

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
      default: `confirm-${randomUUID()}`
    },
    vertical: {
      type: Boolean,
      default: false
    },
    reverse: {
      type: Boolean,
      default: false
    },
    value: {
      default: null
    }
  },
  data() {
    return {
      isVisible: false
    }
  },
  computed: {
    wrapperClass() {
      return this.vertical? 'd-md-flex flex-column' : 'd-md-flex';
    },
    hiddenClass() {
      const classes = [this.vertical? 'flex-grow-0': 'flex-grow-1'];
      if (!this.isVisible) {
        classes.push('visually-hidden');
      }
      return classes;
    },
    cardClass() {
      return this.vertical? 'flex-column align-items-stretch': 'align-items-center';
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