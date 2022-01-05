<template>
  <nav class="navbar bg-navbar navbar-dark navbar-expand-sm">
    <div class="container-fluid">
      <RouterLink class="navbar-brand" :to="{name: 'schema-list'}">
        <img src="./assets/logo.svg" style="height: 2.5rem;" class="me-1" alt="SUSE">
        <i>aimaas</i>
      </RouterLink>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse"
              data-bs-target="#navbarSupportedContent" aria-controls="navbarSupportedContent"
              aria-expanded="false" aria-label="Toggle navigation">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarSupportedContent">
        <ul class="navbar-nav me-auto mb-2 mb-lg-0">
          <SchemaList v-model="activeSchema" :as-dropdown="true" ref="schemalist"/>
          <ReviewNav ref="pendingrequests"/>
          <AuthNav/>
        </ul>
      </div>
    </div>
  </nav>
  <AlertDisplay/>
  <div class="container mt-2">
    <router-view v-slot="{Component}">
      <keep-alive>
        <component :is="Component"/>
      </keep-alive>
    </router-view>
  </div>

</template>
<style>
.eos-icons {
  font-size: 120%;
  line-height: 120%;
  vertical-align: text-top;
}
</style>
<script>
import {computed} from "vue";
import 'bootstrap/dist/js/bootstrap.min.js';
import "eos-icons/dist/css/eos-icons.css";
import "suse-bootstrap5-theme/dist/css/suse.css";

import AuthNav from "@/components/auth/AuthNav";
import AlertDisplay from "@/components/alerts/AlertDisplay";
import SchemaList from "@/components/SchemaList";
import ReviewNav from "@/components/change_review/ReviewNav";

export default {
  name: 'App',
  components: {SchemaList, AlertDisplay, AuthNav, ReviewNav},
  data: function () {
    return {
      activeSchema: null
    }
  },
  provide() {
    return {
      activeSchema: computed(() => this.activeSchema),
      availableSchemas: computed(() => this.$refs.schemalist.schemas),
      pendingRequests: computed(() => this.$refs.pendingrequests.changes),
      updatePendingRequests: this.onPendingReviews
    }
  },
  computed: {
    availableSchemas() {
      let _avail_schemas = {};
      if (this.$refs.schemalist && this.$refs.schemalist.schemas) {
        for (let schema of this.$refs.schemalist.schemas) {
          _avail_schemas[schema.slug] = schema;
        }
      } else {
        console.warn("List of available schemas not ready, yet");
      }
      return _avail_schemas
    }
  },
  methods: {
    onPendingReviews() {
      this.$refs.pendingrequests.load();
    },
    async getSchemaFromRoute() {
      let schemaSlug = this.$route.params.schemaSlug || null;
      if (!schemaSlug) {
        return null;
      }
      if (Object.keys(this.availableSchemas).length < 1) {
        if (!this.$refs.schemalist) {
          console.warn("Schema list not ready, yet")
          return
        }
        await this.$refs.schemalist.load();
      }
      try {
        // First, try to reuse data in storage
        this.activeSchema = this.availableSchemas[schemaSlug];
      } catch (e) {
        this.activeSchema = await this.$api.getSchema({slugOrId: schemaSlug});
      }
    }
  },
  watch: {
    $route: {
      handler: "getSchemaFromRoute",
      immediate: true, // runs immediately with mount() instead of calling method on mount hook
    },
  }
}
</script>