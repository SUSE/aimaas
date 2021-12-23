<template>
  <ul class="list-group">
    <template v-if="!loading">
      <li class="list-group-item" v-for="change in changes" :key="change.id">
        <h5 class="text-black py-2 px-3 d-flex" :class="`bg-${CHANGE_STATUS_MAP[change.status]}`"
            data-bs-toggle="tooltip" :title="change.status">
          <span v-if="change.reviewed_at" data-bs-toggle="tooltip" title="Reviewed at"
                class="flex-grow-1">
            {{ formatDate(change.reviewed_at) }}
          </span>
          <span v-else class="flex-grow-1" data-bs-toggle="tooltip" title="Created at">
            {{ formatDate(change.created_at) }}
          </span>
          <span v-if="change.reviewed_by" data-bs-toggle="tooltip" title="Reviewed by"
                class="flex-grow-1">
            {{ change.reviewed_by }}
          </span>
          <span v-else class="flex-grow-1" data-bs-toggle="tooltip" title="Created by">
            {{ change.created_by }}
          </span>
        </h5>
        <div v-if="change.reviewed_at" class="mb-3">
          <div class="row">
            <div class="col-4">Created by:</div>
            <div class="col-8">{{ change.created_by }}</div>
          </div>
          <div class="row">
            <div class="col-4">Created at:</div>
            <div class="col-8">{{ change.created_at }}</div>
          </div>
        </div>
        <template v-if="change.id in changeDetails">
          <template v-if="changeDetails[change.id].length > 0">
            <div v-for="(details, idx) in changeDetails[change.id]" :key="`${change.id}/${idx}`"
                 class="row border-light border-bottom">
              <div class="col-1">
                <i class="eos-icons">{{ CHANGE_STATUS_MAP[details.action] }}</i>
              </div>
              <div class="col-11">
                <div class="row" v-for="(value, key) of details"
                     :key="`${change.id}/${idx}/${key}`">
                  <div class="col-4">
                    {{ key }}
                  </div>
                  <div class="col-8">
                    {{ value }}
                  </div>
                </div>
              </div>
            </div>
          </template>
          <div v-else class="alert alert-info">No additional details.</div>
        </template>
        <button v-else type="button" class="btn btn-link" @click="loadDetails(change.id)">
          Load details
        </button>
      </li>
    </template>
    <li v-else class="list-group-item placeholder-glow">
      <span class="placeholder col-8"></span>
    </li>
  </ul>
</template>

<script>
import {formatDate, CHANGE_STATUS_MAP} from "@/utils";

export default {
  name: "Changes",
  props: {
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
      loading: true,
      changes: [],
      changeDetails: {},
      CHANGE_STATUS_MAP
    }
  },
  async created() {
    this.changes = await this.$api.getChangeRequests({
      schemaSlug: this.schema.slug,
      entityIdOrSlug: this.entitySlug
    });
    this.loading = false;
  },
  methods: {
    formatDate,
    async transformSchemaDetails(details) {
      const transformed = [];
      for (const action of ['add', 'delete', 'update']) {
        for (let change of details.changes[action]) {
          change.action = action;
          transformed.push(change);
        }
      }
      return transformed;
    },
    async transformEntityDetails(details) {
      const transformed = [];

    },
    async transformDetails(details) {
      if (!this.entitySlug) {
        return this.transformSchemaDetails(details);
      }

    },
    async loadDetails(changeId) {
      if (changeId in this.changeDetails) {
        return;
      }
      const details = await this.$api.getChangeRequestDetails({
        schemaSlug: this.schema.slug,
        changeId: changeId,
        entityIdOrSlug: this.entitySlug
      });
      this.changeDetails[changeId] = await this.transformDetails(details);
    }
  }
}
</script>

<style scoped>

</style>