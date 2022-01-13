<template>
  <div class="d-flex flex-wrap gap-3">
    <div v-for="eId in entityIds" :key="eId">
      <RefEntity :schema-slug="schemaSlug" :entity-id="eId"/>
    </div>
  </div>
</template>

<script>
import RefEntity from "@/components/RefEntity";

export default {
  name: "RefEntityList",
  components: {RefEntity},
  props: {
    schemaSlug: {
      required: true,
      type: String
    },
    entityIds: {
      required: true,
      type: Array
    }
  }
}
</script>

<style scoped>

</style>