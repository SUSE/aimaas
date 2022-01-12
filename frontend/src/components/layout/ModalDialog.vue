<template>
  <button type="button" class="btn" :class="toggleButton.css" data-bs-toggle="modal"
          :data-bs-target="`#${uniqueId}`">
    <slot name="button">
      <i v-if="toggleButton.icon" class='eos-icons me-1'>{{ toggleButton.icon }}</i>
      {{ toggleButton.text }}
    </slot>
  </button>
  <div class="modal" :id="uniqueId">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">{{ modalTitle }}</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"/>
        </div>
        <div class="modal-body">
          <slot name="content">
            <div class="alert alert-warning">You need to define the content of your modal!</div>
          </slot>
        </div>
        <div class="modal-footer d-flex">
          <button type="button" class="btn btn-outline-dark flex-grow-1" data-bs-dismiss="modal">
            <i class='eos-icons me-1'>close</i>
            Close
          </button>
          <button v-for="mbtn of modalButtons" :key="mbtn.id" type="button"
                  class="btn flex-grow-1" :class="mbtn.css" data-bs-dismiss="modal"
                  @click="mbtn.callback">
            <i v-if="mbtn.icon" class='eos-icons me-1'>{{ mbtn.icon }}</i>
            {{  mbtn.text }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import {randomUUID} from "@/utils";
import {Button, ModalButton} from "@/composables/modals";

export default {
  name: "ModalDialog",
  props: {
    toggleButton: {
      required: true,
      type: Button
    },
    modalButtons: {
      required: true,
      type: Array,
      validator(value) {
        for (const mb of value) {
          if (!(mb instanceof ModalButton)) {
            return false;
          }
        }
        return true;
      }
    },
    modalId: {
      required: false,
      type: String
    },
    modalTitle: {
      required: false,
      type: String,
      default: ""
    }
  },
  computed: {
    uniqueId() {
      return this.modalId || `modal-${randomUUID()}`;
    }
  }
}
</script>

<style scoped>

</style>