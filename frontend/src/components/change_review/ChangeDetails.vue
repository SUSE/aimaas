<template>
  <Placeholder :loading="loading" :big="true">
    <template v-slot:content>
      <template v-if="changeId in changeDetails && changeDetails[changeId]">
        <small v-if="!isBound">
          This change request targets schema
          <router-link
              :to="{name: 'schema-view', params: {schemaSlug: changeDetails[changeId].entity.schema}}">
            {{ changeDetails[changeId].entity.schema }}
          </router-link>
          <template v-if="changeDetails[changeId].change_type === 'UPDATE'">
            and updates entity
            <router-link :to="{name: 'entity-view', params: {schemaSlug: changeDetails[changeId].entity.schema, entitySlug: changeDetails[changeId].entity.slug}}">
              {{ changeDetails[changeId].entity.slug }}
            </router-link>
          </template>.
        </small>
        <div class="table-responsive">
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
      </template>
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
import Placeholder from "@/components/layout/Placeholder.vue";

export default {
  name: "ChangeDetails",
  components: {Placeholder},
  props: {
    changeId: {
      required: true,
      type: Number
    },
    objectType: {
      type: String,
      required: true,
      validator(value) {
        return ["SCHEMA", "ENTITY"].includes(value);
      }
    },
    schema: {
      required: true,
      type: Object
    },
    entitySlug: {
      required: false,
      type: String,
      default: '0'
    },
    isBound: {
      required: true,
      type: Boolean
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
      await loadChangeDetails(this.$api, this.objectType.toLowerCase(), this.changeId,
          this.changeDetails, null);
      this.loading = false;
    }
  }
}
</script>

<style scoped>

</style>
