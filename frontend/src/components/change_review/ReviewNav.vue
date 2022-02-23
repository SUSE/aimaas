<template>
  <li class="nav-item" data-bs-toggle="tooltip" :title="toolTip">
    <router-link class="nav-link text-nowrap" :to="{name: 'review-list'}">
        <i class='eos-icons me-1'>thumbs_up_down</i>
        Reviews
        <sup class="badge rounded-pill bg-danger text-light smal" v-if="count > 0">
          {{ count }}
        </sup>
    </router-link>
  </li>
</template>

<script>
export default {
  name: "ReviewNav",
  data() {
    return {
      count: 0
    };
  },
  computed: {
    toolTip() {
      if (this.count) {
        return `Change requests awaiting review: ${this.count}`;
      }
      return "";
    }
  },
  async created() {
    await this.load();
  },
  methods: {
    async load() {
      const response = await this.$api.getCountOfPendingChangeRequests();
      this.count = response?.count || 0;
    }
  }
}
</script>

<style scoped>

</style>