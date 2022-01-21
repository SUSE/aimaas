<template>
  <li class="nav-item" data-bs-toggle="tooltip" :title="toolTip">
    <router-link class="nav-link" :to="{name: 'review-list'}">
        <i class='eos-icons me-1'>thumbs_up_down</i>
        Reviews
        <sup class="badge rounded-pill bg-danger text-light smal" v-if="numberOfOpenReviews > 0">
          {{ numberOfOpenReviews}}
        </sup>
    </router-link>
  </li>
</template>

<script>
export default {
  name: "ReviewNav",
  data() {
    return {
      changes: []
    };
  },
  computed: {
    numberOfOpenReviews() {
      return this.changes?.length || 0;
    },
    toolTip() {
      if (this.numberOfOpenReviews) {
        return `Change requests awaiting review: ${this.numberOfOpenReviews}`;
      }
      return "";
    }
  },
  async created() {
    await this.load();
  },
  methods: {
    async load() {
      this.changes = await this.$api.getPendingChangeRequests();
    }
  }
}
</script>

<style scoped>

</style>