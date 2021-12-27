<template>
  <ul class="list-group">
    <Placeholder :loading="loading">
      <template v-slot:content>
        <li class="list-group-item" v-for="change in changes" :key="change.id">
          <div class="row text-black p-2" :class="`bg-${CHANGE_STATUS_MAP[change.status]}`">
            <div class="col-3 d-flex flex-column align-items-end">
              <small>Created at:</small>
              <span>{{ formatDate(change.created_at) }}</span>
            </div>
            <div class="col-2 d-flex flex-column align-items-end">
              <small>Created by:</small>
              <span>{{ change.created_by }}</span>
            </div>
            <template v-if="change.reviewed_at">
              <div class="col-3 d-flex flex-column align-items-end border-start border-dark">
                <small>Reviewed at:</small>
                <span>{{ formatDate(change.reviewed_at) }}</span>
              </div>
              <div class="col-2 d-flex flex-column align-items-end">
                <small>Reviewed by:</small>
                <span>{{ change.reviewed_by }}</span>
              </div>
              <div class="col-2 d-flex flex-column align-items-end">
                <small>Comment:</small>
                <small>{{ change.comment }}</small>
              </div>
            </template>
            <div v-else class="col-7 d-flex gap-3 p-0 m-0">
              <button type="button" class="btn btn-outline-danger flex-grow-1 shadow-sm"
                      data-bs-toggle="tooltip" title="Decline request and do not apply changes.">
                <i class="eos-icons me-1">thumb_down</i>
                Decline
              </button>
              <button type="button" class="btn btn-success flex-grow-1 shadow-sm"
                      data-bs-toggle="tooltip" title="Accept request and apply changes to database.">
                <i class="eos-icons me-1">thumb_up</i>
                Approve
              </button>
            </div>
          </div>
          <SchemaChangeDetails v-if="!entitySlug" :changeId="change.id" :schema="schema"/>
          <EntityChangeDetails v-else :changeId="change.id" :schema="schema"
                               :entitySlug="entitySlug"/>
        </li>
      </template>
    </Placeholder>
  </ul>
</template>

<script>
import {formatDate, CHANGE_STATUS_MAP} from "@/utils";
import Placeholder from "@/components/layout/Placeholder";
import EntityChangeDetails from "@/components/change_review/EntityChangeDetails";
import SchemaChangeDetails from "@/components/change_review/SchemaChangeDetails";

export default {
  name: "Changes",
  components: {SchemaChangeDetails, Placeholder, EntityChangeDetails},
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
    formatDate
  }
}
</script>

<style scoped>

</style>