<template>
  <div v-if="loading" class="placeholder-glow">
    <slot name="placeholder">
      <template v-if="big">
        <span class="placeholder col-2 me-1"></span>
        <span class="placeholder col-5 me-1"></span>
        <span class="placeholder col-4 me-1"></span>
        <span class="placeholder col-1 me-1"></span>
        <span class="placeholder col-7 me-1"></span>
        <span class="placeholder col-3 me-1"></span>
        <span class="placeholder col-3 me-1"></span>
        <span class="placeholder col-4 me-1"></span>
        <span class="placeholder col-4 me-1"></span>
      </template>
      <span v-else class="placeholder col-8"></span>
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
    },
    big: {
      type: Boolean,
      default: false
    }
  }
}
</script>

<style scoped>

</style>