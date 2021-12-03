<template>
  <p>Recent changes</p>
  <template v-if="changes">
    <ul class="list-group">
      <template v-for="change in changes" :key="change.id">
        <li class="list-group-item">
          <RouterLink :to="`/changes/entity/${schemaSlug}/${entitySlug}/${change.id}`">
            {{
              new Date(change.reviewed_at || change.created_at).toLocaleString()
            }}
            <span
              :class="`badge rounded-pill ${
                this.REVIEW_STATUS_BG_MAP[change.status]
              }`"
              >{{ change.status }}</span
            ></RouterLink
          >
        </li>
      </template>
    </ul>
  </template>
  <template v-else> </template>
</template>

<script>
import { api } from "../api";

const REVIEW_STATUS_BG_MAP = {
  APPROVED: "bg-success",
  PENDING: "bg-primary",
  DECLINED: "bg-secondary",
};

export default {
  name: "RecentChangesSidebar",
  props: ["schemaSlug", "entitySlug"],
  data() {
    return {
      changes: null,
      REVIEW_STATUS_BG_MAP
    };
  },
  created() {
    api
      .getRecentEntityChanges({
        schemaSlug: this.schemaSlug,
        entityIdOrSlug: this.entitySlug,
      })
      .then((resp) => resp.json())
      .then((json) => (this.changes = json));
  },
};
</script>
