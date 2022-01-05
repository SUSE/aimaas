<template>
  <div v-if="loading" class="d-flex justify-content-center">
    <div class="spinner-border" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
  </div>
  <slot v-else></slot>
</template>

<script>
export default {
  name: "Spinner",
  props: ['loading']
}
</script>

<style scoped>

</style>