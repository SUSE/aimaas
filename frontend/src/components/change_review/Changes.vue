<template>
  <ul class="list-group">
    <Placeholder :loading="loading">
      <template v-slot:content>
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