<template>
  <BaseLayout>
    <template v-slot:additional_breadcrumbs>
      <li class="breadcrumb-item">{{ schemaName }}</li>
      <li class="breadcrumb-item active">Entities</li>
    </template>
    <template v-slot:actions>
      <RouterLink
          v-if="this.activeSchema"
          :to="`/${this.activeSchema.slug}`"
          class="btn btn-primary"
          data-bs-toggle="tooltip"
          data-bs-placement="bottom"
          title="View schema structure">
        <i class="eos-icons">visibility</i>
        View
      </RouterLink>
      <RouterLink
          v-if="this.activeSchema"
          :to="`/edit/${this.activeSchema.slug}`"
          class="btn btn-primary ms-1"
          data-bs-toggle="tooltip"
          data-bs-placement="bottom"
          title="Edit schema structure">
        <i class="eos-icons">mode_edit</i>
        Edit
      </RouterLink>
      <RouterLink
          v-if="this.activeSchema"
          :to="`/${this.activeSchema?.slug}/entities/new`"
          class="btn btn-secondary ms-1"
          data-bs-toggle="tooltip"
          data-bs-placement="bottom"
          title="Add new entity to schema">
        <i class="eos-icons">add</i>
        Add
      </RouterLink>
    </template>
  </BaseLayout>

  <SearchPanel
      @search="setFiltersAndSearch"
      :key="this.activeSchema?.slug"
      :filterableFields="this.filterableFields"
      :operators="this.operators"/>
  <Pagination
      v-if="this.totalEntities > this.entitiesPerPage"
      v-on:goTo="changePage"
      :totalEntities="this.totalEntities"
      :entitiesPerPage="this.entitiesPerPage"
      :currentPage="this.currentPage"/>

  <div class="row mb-1">
    <div class="col-2">
      <label for="entitiesLimit"><small>Entities per page</small></label>
    </div>
    <div class="col-1">
      <select v-model="entitiesPerPage" id="entitiesLimit" class="form-select form-select-sm">
        <option>10</option>
        <option>30</option>
        <option>50</option>
      </select>
    </div>
    <div class="col-9 text-end">
      <small>{{ this.totalEntities }} result(s)</small>
    </div>
  </div>
  <EntityListTable
      @reorder="this.reorder"
      :entities="this.entities"
      :schemaSlug="this.activeSchema?.slug"/>

  <Pagination
      v-if="this.totalEntities > this.entitiesPerPage"
      v-on:goTo="changePage"
      :totalEntities="this.totalEntities"
      :entitiesPerPage="this.entitiesPerPage"
      :currentPage="this.currentPage"
  />
</template>

<script>
import BaseLayout from "@/components/layout/BaseLayout";
import Pagination from "./Pagination.vue";
import EntityListTable from "./EntityListTable.vue";
import SearchPanel from "./SearchPanel.vue";
import {api} from "@/api";

export default {
  components: {BaseLayout, Pagination, EntityListTable, SearchPanel},
  name: "EntityList",
  async created() {
  },
  computed: {
    schemaName() {
      console.debug("Schema name", this.activeSchema);
      try {
        return this.activeSchema.name;
      } catch (e) {
        console.error("No schema name?", this.activeSchema)
        return "---";
      }
    },
    offset() {
      return (this.currentPage - 1) * this.entitiesPerPage;
    },
    pages() {
      return Math.ceil(this.totalEntities / this.entitiesPerPage);
    },
  },
  watch: {
    entitiesPerPage() {
      this.getEntities({resetPage: true});
    },
    async activeSchema() {
      this.filters = {};
      const response = await api.getEntities({
        schemaSlug: this.activeSchema.slug,
        limit: this.entitiesPerPage,
        offset: this.offset,
        meta: true,
      });
      const json = await response.json();
      this.entities = json.entities;
      this.totalEntities = json.total;
      this.operators = json.meta.filter_fields.operators;
      this.filterableFields = json.meta.filter_fields.fields;
    }
  },
  methods: {
    async changePage(page) {
      this.currentPage = page;
      await this.getEntities();
    },
    async getEntities({resetPage = false} = {}) {
      if (resetPage) {
        this.currentPage = 1;
      }
      const response = await api.getEntities({
        schemaSlug: this.activeSchema.slug,
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
      this.getEntities({resetPage: true});
    },
    async reorder({orderBy, ascending} = {}) {
      this.orderBy = orderBy;
      this.ascending = ascending;
      this.getEntities();
    },
  },
  data() {
    return {
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
  inject: ['activeSchema']
};
</script>

