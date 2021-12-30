<template>
  <Placeholder :loading="loading">
    <template v-slot:content>
      <RouterLink v-if="entityId"
                  :to="{name: 'entity-view', params: {schemaSlug: schemaSlug, entitySlug: entity.slug}}">
        {{ entity.name }}
      </RouterLink>
    </template>
  </Placeholder>
</template>

<script>
import Placeholder from "@/components/layout/Placeholder";

export default {
  name: "RefEntity",
  components: {Placeholder},
  props: {
    schemaSlug: {
      required: true,
      type: String
    },
    entityId: {
      required: false,
      type: Number
    }
  },
  data() {
    return {
      loading: true,
      entity: null
    }
  },
  async mounted() {
    if (this.entityId) {
      this.loading = true;
      const params = {schemaSlug: this.schemaSlug, entityIdOrSlug: this.entityId};
      this.entity = await this.$api.getEntity(params);
      this.loading = false;
    } else {
      this.loading = false;
    }
  }
}
</script>

<style scoped>

</style>