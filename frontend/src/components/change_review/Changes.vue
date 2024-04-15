<template>
  <BaseLayout v-if="!isBound">
    <template v-slot:additional_breadcrumbs>
      <li class="breadcrumb-item active">Pending reviews</li>
    </template>
  </BaseLayout>
  <AutoPagination :get-func="load" :the-component="pageComponent"
                  :args-for-binding="{isBound: isBound, schema: schema, entitySlug: entitySlug}"/>
</template>

<script>
import { markRaw } from "vue";
import AutoPagination from "@/components/layout/AutoPagination";
import BaseLayout from "@/components/layout/BaseLayout";
import ChangePage from "@/components/change_review/ChangePage";

export default {
  name: "Changes",
  components: {AutoPagination, BaseLayout},
  inject: ["updatePendingRequests"],
  props: {
    schema: {
      required: false,
      type: Object,
      default: null
    },
    entitySlug: {
      required: false,
      type: String,
      default: null
    }
  },
  data() {
    return {
      pageComponent: markRaw(ChangePage)
    }
  },
  computed: {
    isBound() {
      return !(!this.schema && !this.entitySlug);
    }
  },
  methods: {
    async load({page, size} = {}) {
      if (!this.schema) {
        return this.$api.getPendingChangeRequests({page: page, size: size});
      } else {
        return this.$api.getChangeRequests({
          schemaSlug: this.schema.slug,
          entityIdOrSlug: this.entitySlug,
          page: page,
          size: size
        });
      }
    },

  },
  watch: {
    async schema() {
      await this.load();
    },
    async entitySlug() {
      await this.load();
    }
  }
}
</script>

<style scoped>

</style>