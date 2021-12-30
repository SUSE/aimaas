<template>
  <ConfirmButton :callback="internalCallback" :btn-class="btnClass" :id="id" :vertical="vertical"
                 :value="value">
    <template v-slot:label>
      <slot name="label"></slot>
    </template>
    <template v-slot:confirm>
      <small class="text-muted">Please provide a commit with your confirmation</small>
      <textarea class="form-control" :placeholder="placeholder" v-model="comment"></textarea>
    </template>
  </ConfirmButton>
</template>

<script>
import {randomUUID} from "@/utils";
import ConfirmButton from "@/components/inputs/ConfirmButton";

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