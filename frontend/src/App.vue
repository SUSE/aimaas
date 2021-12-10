<template>
  <nav class="navbar bg-navbar navbar-dark navbar-expand-lg">
    <div class="container-fluid">
      <RouterLink class="navbar-brand" to="/">SUSE <i>aimaas</i></RouterLink>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse"
              data-bs-target="#navbarSupportedContent" aria-controls="navbarSupportedContent"
              aria-expanded="false" aria-label="Toggle navigation">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarSupportedContent">
        <ul class="navbar-nav me-auto mb-2 mb-lg-0">
          <SchemaList v-model="activeSchema"></SchemaList>
        </ul>
      </div>
    </div>
  </nav>
  <div class="container mt-2">
    <router-view v-slot="{ Component }">
      <keep-alive include="EntityList">
        <component :is="Component"/>
      </keep-alive>
    </router-view>
  </div>

</template>
<style>
.eos-icons {
  font-size: 120%;
  line-height: 120%;
  vertical-align: top;
}
</style>
<script>
import {computed} from "vue";
import 'bootstrap/dist/js/bootstrap.min.js';
import "eos-icons/dist/css/eos-icons.css";
import "suse-bootstrap5-theme/dist/css/suse.css";

import SchemaList from "@/components/SchemaList";

export default {
  name: 'App',
  metaInfo: {
    title: 'SUSE aimaas'
  },
  components: {SchemaList, },
  data: function () {
    return {
      activeSchema: null
    }
  },
  provide() {
    return {
      activeSchema: computed(() => this.activeSchema)
    }
  },
}
</script>