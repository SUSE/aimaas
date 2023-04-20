<template>
  <BaseLayout>
    <template v-slot:additional_breadcrumbs>
      <li class="breadcrumb-item active">
        <router-link :to="{name: 'schema-view', params: {schemaSlug: activeSchema?.slug || 'n-a'}}">
          {{ activeSchema?.name || 'n/a' }}
        </router-link>
      </li>
      <li class="breadcrumb-item active">Bulk Editor</li>
    </template>
  </BaseLayout>
  <Placeholder :big="true" :loading="loading">
    <template v-slot:content>
      <div v-for="e of entities" :key="e.id" class="border mb-3 p-2">
        <EntityForm :entity="e" :schema="activeSchema"
                    :batch-mode="true"  :ref="`e_form_${e.id}`" v-on:save-all="saveAll" />
      </div>
    </template>
  </Placeholder>
</template>

<script>
import BaseLayout from "@/components/layout/BaseLayout";
import EntityForm from "@/components/inputs/EntityForm";
import Placeholder from "@/components/layout/Placeholder.vue";

export default {
  name: "EntityBulkEdit",
  components: {BaseLayout, EntityForm, Placeholder},
  inject: ['activeSchema'],
  data() {
    return {
      entities: [],
      loading: true
    }
  },
  computed: {
    entityIds() {
      return this.entities.map(x => x.id);
    }
  },
  methods: {
    async getEntityData() {
      const schemaSlug = this.$route.params.schemaSlug;
      if (!schemaSlug) {
        return
      }

      const queryIds = (this.$route.query?.entity || []);
      this.entities = this.entities.filter(x => queryIds.includes(x.id));
      this.loading = true;
      const promises = queryIds
          .map(x => parseInt(x))
          .filter(x => !this.entityIds.includes(x))
          .map(x => this.$api.getEntity({schemaSlug: schemaSlug, entityIdOrSlug: x}));
      Promise.all(promises).then(x => {
        this.entities = this.entities.concat(x);
        this.loading = false;
      })
    },
    async saveAll() {
      const promises = Object.entries(this.$refs)
          .filter(x => x[0].startsWith("e_form_"))
          .map(x => x[1][0].updateEntity());
      Promise.all(promises).then(x => {
        if (x.every(y => y === null)) {
          this.$alerts.push(
              "warning",
              "None of the entities were changed. Therefore no changes were sent to server."
          );
        }
      });
    }
  },
  watch: {
    $route: {
      handler: "getEntityData",
      immediate: true,
      deep: true
    },
  }
}
</script>

<style scoped>

</style>
