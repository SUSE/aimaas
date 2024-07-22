<template>
  <ConfirmButton :callback="internalCallback" :btn-class="btnClass" :id="id" :vertical="vertical"
                 :value="value">
    <template v-slot:label>
      <slot name="label"></slot>
    </template>
    <template v-slot:confirm>
      <small class="text-muted">{{ prompt }}</small>
      <textarea v-if="inputType === 'textarea'" class="form-control" :placeholder="placeholder"
                v-model="comment">
      </textarea>
      <input v-else class="form-control" :placeholder="placeholder" v-model="comment"/>
    </template>
  </ConfirmButton>
</template>

<script>
import {randomUUID} from "@/utils";
import ConfirmButton from "@/components/inputs/ConfirmButton.vue";

export default {
  name: "ConfirmWithComment",
  components: {ConfirmButton},
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
    value: {
      default: null
    },
    placeholder: {
      type: String,
      required: false
    },
    prompt: {
      type: String,
      required: false,
      default: "Please provide a comment with your confirmation"
    },
    inputType: {
      type: String,
      required: false,
      default: "textarea",
      validator(value) {
        return ['input', 'textarea'].includes(value);
      }
    }
  },
  data() {
    return {
      comment: ''
    }
  },
  methods: {
    internalCallback(event) {
      this.callback(event, this.comment);
    }
  }
}
</script>

<style scoped>

</style>
