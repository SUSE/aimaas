<template>
  <template v-if="this.change">
    <h4 class="mt-3">
      <span :class="`badge rounded-pill ${this.statusDisplayClass}`">{{
        this.change.status.toLowerCase()
      }}</span>
      change request for entity
      <RouterLink
        :to="`/${this.$route.params.schema}/${this.$route.params.entity}`"
        >{{ this.change.entity.name }}</RouterLink
      >
    </h4>
    <small
      >Created at: {{ formatDate(this.change.created_at) }} by:
      {{ this.change.created_by }}</small
    >
    <template v-if="change.reviewed_at">
      <p>
        <small
          >Reviewed at: {{ formatDate(this.change.reviewed_at) }} by:
          {{ this.change.reviewed_by }}</small
        >
      </p>
    </template>
    <h4>Changes</h4>
    <table class="table table-bordered table-sm">
      <thead>
        <th>Attribute</th>

        <th v-if="this.change.status != 'PENDING'">Previous value</th>
        <th v-else>Current value</th>

        <th>New value</th>

        <th v-if="this.change.status == 'PENDING'">Value at submit time</th>
      </thead>
      <tbody>
        <tr v-for="(change, attr, index) in this.change.changes" :key="index">
          <td class="col">{{ attr }}</td>

          <td v-if="this.change.status != 'PENDING'" class="col">
            {{ change.old }}
          </td>
          <td v-else class="col">{{ change.current }}</td>

          <td v-if="this.change.status == 'APPROVED'" class="col">
            {{ change.current }}
          </td>
          <td v-else class="col">{{ change.new }}</td>

          <td v-if="this.change.status == 'PENDING'" class="col">
            {{ change.old }}
          </td>
        </tr>
      </tbody>
    </table>

    <template v-if="this.change.status == 'PENDING'">
      <label for="comment">Comment:</label>
      <textarea id="comment" class="form-control mb-3" v-model="this.comment" />
      <button class="btn btn-success" @click="this.reviewChanges('APPROVE')">
        Approve
      </button>
      <button
        class="ms-3 btn btn-outline-danger"
        @click="this.reviewChanges('DECLINE')"
      >
        Decline
      </button>
    </template>
    <template v-else-if="this.change.comment">
      <h4>Comment</h4>
      <p>{{ change.comment }}</p>
    </template>
  </template>
  <template v-else>Loading</template>
</template>

<script>
import { api } from "../api";

const STATUS_CLASSES = {
  APPROVED: "bg-success",
  DECLINED: "bg-secondary",
  PENDING: "bg-primary",
};

export default {
  name: "EntityChangeDetails",
  emits: [],
  async created() {
    const resp = await api.getEntityChangeDetails({
      schemaSlug: this.$route.params.schema,
      entityIdOrSlug: this.$route.params.entity,
      changeId: this.$route.params.changeId,
    });
    this.change = await resp.json();
  },
  computed: {
    statusDisplayClass() {
      return STATUS_CLASSES[this.change.status];
    },
  },
  data() {
    return {
      change: null,
      comment: null,
    };
  },
  methods: {
    formatDate(date) {
      return new Date(date).toLocaleString();
    },
    async reviewChanges(verdict) {
      const resp = await api.reviewChanges({
        verdict,
        changeId: this.$route.params.changeId,
        changeObject: "ENTITY",
        changeType: "UPDATE",  // TODO this is not going to work for creating/deleting entities, but maybe they will have separate components
        comment: this.comment,
      });
      if (resp.status == 200) {
        this.$router.push(
          `/${this.change.entity.schema}/${
            this.change.changes.slug?.new || this.change.entity.slug
          }`
        );
      }
    },
  },
};
</script>