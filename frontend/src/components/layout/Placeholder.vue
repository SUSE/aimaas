<template>
  <div v-if="loading" class="placeholder-glow">
    <slot name="placeholder">
      <span class="placeholder col-8"></span>
    </slot>
  </div>
  <slot v-else name="content"></slot>
</template>

<script>
export default {
  name: "Placeholder",
  props: {
    loading: {
      type: Boolean,
      default: true
    }
  }
}
</script>

<style scoped>

</style>