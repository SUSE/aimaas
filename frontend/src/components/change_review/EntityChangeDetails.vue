<template>
  <Placeholder :loading="loading" :big="true">
    <template v-slot:content>
      <div class="table-responsive" v-if="changeId in changeDetails && changeDetails[changeId]">
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
      </div>
      <div v-else-if="changeId in changeDetails && !changeDetails[changeId]"
           class="alert alert-warning mt-2">
        Cannot load details or none available.
      </div>
      <button v-else type="button" class="btn btn-link" @click="loadDetails()">
        Load details
      </button>
    </template>
  </Placeholder>
</template>

<script>
import {CHANGE_STATUS_MAP} from "@/utils";
import {loadChangeDetails} from "@/composables/changes";
import Placeholder from "@/components/layout/Placeholder";

export default {
  name: "EntityChangeDetails",
  components: {Placeholder},
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
      default: '0'
    }
  },
  data() {
    return {
      CHANGE_STATUS_MAP,
      changeDetails: {},
      loading: false
    }
  },
  methods: {
    async loadDetails() {
      this.loading = true;
      await loadChangeDetails(this.$api, "entity", this.changeId,
          this.changeDetails, null);
      this.loading = false;
    }
  }
}
</script>

<style scoped>

</style>