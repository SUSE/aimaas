<template>
  <template v-if="changeId in changeDetails">
    <table class="table">
      <thead>
      <tr>
        <th>Field</th>
        <th>New value</th>
        <th>Old value</th>
        <th>Current value</th>
      </tr>
      </thead>
      <tbody>
      <tr v-for="(values, slug) of changeDetails[changeId].changes" :key="slug">
        <th>{{ slug }}</th>
        <td>{{ values.new }}</td>
        <td>{{ values.old }}</td>
        <td>{{ values.current }}</td>
      </tr>
      </tbody>
    </table>
  </template>
  <button v-else type="button" class="btn btn-link" @click="loadDetails()">
    Load details
  </button>
</template>

<script>
import {CHANGE_STATUS_MAP} from "@/utils";
import {loadChangeDetails} from "@/composables/changes";

export default {
  name: "EntityChangeDetails",
  props: {
    changeId: {
      required: true,
      type: Number
    },
    schema: {
      required: true,
      type: Object
    },
    entitySlug: {
      required: false,
      type: String,
      default: null
    }
  },
  data() {
    return {
      CHANGE_STATUS_MAP,
      changeDetails: {}
    }
  },
  methods: {
    async loadDetails() {
      return loadChangeDetails(this.$api, this.schema.slug, this.entitySlug, this.changeId,
          this.changeDetails, null);
    }
  }
}
</script>

<style scoped>

</style>