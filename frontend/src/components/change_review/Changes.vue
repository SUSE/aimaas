<template>
  <ul class="list-group">
    <Placeholder :loading="loading">
      <template v-slot:content>
        <li class="list-group-item" v-for="change in changes" :key="change.id">
          <div class="row text-black p-2" :class="`bg-${CHANGE_STATUS_MAP[change.status]}`">
            <div class="col-md-1 d-flex flex-column align-items-end">
              <small>Action:</small>
              <span>{{ change.change_type }}</span>
            </div>
            <div class="col-md-2 d-flex flex-column align-items-end">
              <small>Created at:</small>
              <span>{{ formatDate(change.created_at) }}</span>
            </div>
            <div class="col-md-2 d-flex flex-column align-items-end">
              <small>Created by:</small>
              <span>{{ change.created_by }}</span>
            </div>
            <template v-if="change.reviewed_at">
              <div class="col-md-2 d-flex flex-column align-items-end border-start border-dark">
                <small>Reviewed at:</small>
                <span>{{ formatDate(change.reviewed_at) }}</span>
              </div>
              <div class="col-md-2 d-flex flex-column align-items-end">
                <small>Reviewed by:</small>
                <span>{{ change.reviewed_by }}</span>
              </div>
              <div class="col-md-3 d-flex flex-column align-items-end">
                <small>Comment:</small>
                <small>{{ change.comment }}</small>
              </div>
            </template>
            <div v-else class="col-md-7 d-flex gap-3 p-0 m-0">
              <ConfirmButton :callback="onDecline" btn-class="btn-outline-danger shadow-sm"
                             class="flex-grow-1" data-bs-toggle="tooltip" :vertical="true"
                             title="Decline request and do not apply changes." :value="change.id">
                <template v-slot:label>
                  <i class="eos-icons me-1">thumb_down</i>
                  Decline
                </template>
              </ConfirmButton>
              <ConfirmButton :callback="onApprove" btn-class="btn-success shadow-sm"
                             class="flex-grow-1" data-bs-toggle="tooltip" :vertical="true"
                             title="Accept request and apply changes to database."
                             :value="change.id">
                <template v-slot:label>
                  <i class="eos-icons me-1">thumb_up</i>
                  Approve
                </template>
              </ConfirmButton>
            </div>
          </div>
          <SchemaChangeDetails v-if="change.object_type === 'SCHEMA'" :changeId="change.id"
                               :schema="schema"/>
          <EntityChangeDetails v-else-if="change.object_type === 'ENTITY'" :changeId="change.id"
                               :schema="schema" :entitySlug="entitySlug"/>
        </li>
      </template>
    </Placeholder>
  </ul>
</template>

<script>
import {formatDate, CHANGE_STATUS_MAP} from "@/utils";
import ConfirmButton from "@/components/inputs/ConfirmButton";
import Placeholder from "@/components/layout/Placeholder";
import EntityChangeDetails from "@/components/change_review/EntityChangeDetails";
import SchemaChangeDetails from "@/components/change_review/SchemaChangeDetails";

export default {
  name: "Changes",
  components: {SchemaChangeDetails, Placeholder, EntityChangeDetails, ConfirmButton},
  inject: ["pendingRequests"],
  props: {
    schema: {
      required: false,
      type: Object,
      default: null
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
    await this.load();
  },
  methods: {
    formatDate,
    async load() {
      this.loading = true;
      if (!this.schema) {
        this.changes = this.pendingRequests;
      } else {
        const response = await this.$api.getChangeRequests({
          schemaSlug: this.schema.slug,
          entityIdOrSlug: this.entitySlug
        });
        if (Array.isArray(response)) {
          this.changes = response;
        } else {
          this.changes = Array.prototype.concat(
              response?.pending_entity_requests || [],
              response?.schema_changes || []
          );
        }
      }
      this.loading = false;
    },
    onDecline(event) {
      console.info("TODO: This needs to be implemented", event.target.value);
    },
    onApprove(event) {
      console.info("TODO: This needs to be implemented", event.target.value);
    }
  },
  watch: {
    async schema() {
      await this.load();
    },
    async entitySlug() {
      await this.load();
    }
  }
}
</script>

<style scoped>

</style>