<template>
  <div class="row">
    <div class="col-lg-2">
      <RouterLink
        to="/createSchema"
        class="btn btn-sm btn-outline-primary mt-1 mb-1 d-grid"
        style="text-decoration: none"
        >Create schema</RouterLink
      >
      <SchemaList
        v-on:selectSchema="this.selectSchema"
        :schemas="this.schemas"
        :selectedSchema="this.selectedSchema"
      />
    </div>
    <div class="col-lg-10 table-responsive">
      <h2 v-if="this.selectedSchema" class="mt-1">
        Schema {{ this.selectedSchema.name }}
        <RouterLink
          v-if="this.selectedSchema"
          :to="`/${this.selectedSchema.slug}`"
          class="btn btn-sm btn-primary"
          style="text-decoration: none"
          >View schema</RouterLink
        >
        <RouterLink
          v-if="this.selectedSchema"
          :to="`/edit/${this.selectedSchema.slug}`"
          class="btn btn-sm btn-primary ms-1"
          style="text-decoration: none"
          >Edit schema</RouterLink
        >
        <RouterLink
          :to="`/${this.selectedSchema?.slug}/entities/new`"
          class="btn btn-sm btn-primary ms-1"
          style="text-decoration: none"
          >Create new entity</RouterLink
        >
      </h2>
      <SearchPanel
        @search="setFiltersAndSearch"
        :key="this.selectedSchema?.slug"
        :filterableFields="this.filterableFields"
        :operators="this.operators"
      />
      <Pagination
        v-if="this.totalEntities > this.entitiesPerPage"
        v-on:goTo="changePage"
        :totalEntities="this.totalEntities"
        :entitiesPerPage="this.entitiesPerPage"
        :currentPage="this.currentPage"
      />

      <div class="row">
        <div class="col-11">
          <label for="entitiesLimit"><small>Entities per page</small></label>
          <select v-model="entitiesPerPage" id="entitiesLimit">
            <option>10</option>
            <option>30</option>
            <option>50</option>
          </select>
        </div>
        <div class="col">
          <p>
            <small>{{ this.totalEntities }} results</small>
          </p>
        </div>
      </div>

      <EntityListTable
        @reorder="this.reorder"
        :entities="this.entities"
        :schemaSlug="this.selectedSchema?.slug"
      />
      <Pagination
        v-if="this.totalEntities > this.entitiesPerPage"
        v-on:goTo="changePage"
        :totalEntities="this.totalEntities"
        :entitiesPerPage="this.entitiesPerPage"
        :currentPage="this.currentPage"
      />
    </div>
  </div>
</template>

<script>
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap";
import Pagination from "./Pagination.vue";
import EntityListTable from "./EntityListTable.vue";
import SchemaList from "./SchemaList.vue";
import SearchPanel from "./SearchPanel.vue";
import { api } from "../api";

export default {
  components: { Pagination, EntityListTable, SchemaList, SearchPanel },
  name: "EntityList",
  async created() {
    const response = await api.getSchemas();
    const json = await response.json();
    this.schemas = json.sort((a, b) => (a.name > b.name ? 1 : -1));
    if (this.schemas.length) await this.selectSchema(this.schemas[0]);
  },
  computed: {
    offset() {
      return (this.currentPage - 1) * this.entitiesPerPage;
    },
    pages() {
      return Math.ceil(this.totalEntities / this.entitiesPerPage);
    },
  },
  watch: {
    entitiesPerPage() {
      this.getEntities({ resetPage: true });
    },
  },
  methods: {
    async selectSchema(schema) {
      this.selectedSchema = schema;
      this.filters = {};
      const response = await api.getEntities({
        schemaSlug: schema.slug,
        limit: this.entitiesPerPage,
        offset: this.offset,
        meta: true,
      });
      const json = await response.json();
      this.entities = json.entities;
      this.totalEntities = json.total;
      this.operators = json.meta.filter_fields.operators;
      this.filterableFields = json.meta.filter_fields.fields;
    },
    async changePage(page) {
      this.currentPage = page;
      await this.getEntities();
    },
    async getEntities({ resetPage = false } = {}) {
      if (resetPage) {
        this.currentPage = 1;
      }
      const response = await api.getEntities({
        schemaSlug: this.selectedSchema.slug,
        limit: this.entitiesPerPage,
        offset: this.offset,
        filters: this.filters,
        orderBy: this.orderBy,
        ascending: this.ascending,
      });
      const json = await response.json();
      this.entities = json.entities;
      this.totalEntities = json.total;
    },
    async setFiltersAndSearch(filters) {
      this.filters = filters;
      this.getEntities({ resetPage: true });
    },
    async reorder({ orderBy, ascending } = {}) {
      this.orderBy = orderBy;
      this.ascending = ascending;
      this.getEntities();
    },
  },
  data() {
    return {
      schemas: [],
      selectedSchema: null,
      entities: [],
      entitiesPerPage: 10,
      totalEntities: 0,
      currentPage: 1,
      filterableFields: {},
      operators: {},
      filters: {},
      orderBy: "name",
      ascending: true,
    };
  },
};
</script>

<style scoped>
.list-group {
  max-height: 100vh;
  overflow: scroll;
}
</style>
