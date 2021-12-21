<template>
  <template v-if="asDropdown">
    <li class="nav-item dropdown">
      <a class="nav-link dropdown-toggle" href="#" id="nav-schema-dropdown" role="button"
         data-bs-toggle="dropdown" aria-expanded="false">
        Schema
      </a>
      <ul class="dropdown-menu" aria-labelledby="nav-schema-dropdown">
        <li v-if="loading">
          <div class="dropdown-item placeholder-wave">
            <span class="placeholder col-8"></span>
          </div>
        </li>
        <li v-for="schema in schemas" :key="schema.id">
          <router-link :to="{name: 'schema-view', params: {schemaSlug: schema.slug}}"
                       class="dropdown-item" :class="modelValue?.id === schema.id ? 'active': ''">
            {{ schema.name }}
          </router-link>
        </li>
        <li>
          <hr class="dropdown-divider">
        </li>
        <li>
          <RouterLink
              to="/createSchema"
              class="dropdown-item">
            <i class='eos-icons me-1'>add_circle</i>
            New
          </RouterLink>
        </li>
      </ul>
    </li>
  </template>
  <template v-else>
    <BaseLayout key="/"/>
    <div class="container">
      <h1>Schema selection</h1>
      <div class="list-group">
        <router-link :to="{name: 'schema-view', params: {schemaSlug: schema.slug}}"
                     v-for="schema in schemas" :key="schema.id"
                     class="list-group-item list-group-item-action">
          {{ schema.name }}
        </router-link>
      </div>
    </div>
  </template>
</template>

<script>
import {api} from "@/api";
import BaseLayout from "@/components/layout/BaseLayout";

export default {
  name: "SchemaList",
  props: ["modelValue", "asDropdown"],
  data: function () {
    return {
      schemas: null,
      loading: true
    }
  },

  components: {BaseLayout,},
  computed: {},
  created: function () {
    this.load();
  },
  methods: {
    async load() {
      this.loading = true;
      this.schemas = await api.getSchemas();
      this.loading = false;
    }
  }

};
</script>
