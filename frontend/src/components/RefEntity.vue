<template>
  <Placeholder :loading="loading">
    <template v-slot:content>
      <template v-if="entityId">
        <RouterLink v-if="entity"
                  :to="{name: 'entity-view', params: {schemaSlug: schemaSlug, entitySlug: entity?.slug}}">
        {{ entity.name }}
      </RouterLink>
      <div v-else class="alert alert-warning m-0 px-2 py-1">
        Failed to load
      </div>
      </template>
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
  async activated() {
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
.alert {
  width: 12rem;
  max-width: 25rem;
}
</style>