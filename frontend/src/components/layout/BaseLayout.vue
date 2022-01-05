<template>
  <div class="d-flex">
    <breadcrumbs class="flex-grow-1 me-2">
      <slot name="additional_breadcrumbs" />
    </breadcrumbs>
    <div>
      <slot name="actions" />
    </div>
  </div>
</template>

<script>
import breadcrumbs from "@/components/layout/breadcrumbs";

export default {
  name: "BaseView",
  components: {breadcrumbs},
}
</script>

