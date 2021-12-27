<template>
  <li class="nav-item">
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
  computed: {
    numberOfOpenReviews() {
      return 0;
    }
  }
}
</script>

<style scoped>

</style>