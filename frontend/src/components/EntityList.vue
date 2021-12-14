<template>
  <SearchPanel
      @search="setFiltersAndSearch"
      :key="schema?.slug"
      :filterableFields="filterableFields"
      :operators="operators"/>
  <Pagination
      v-if="totalEntities > entitiesPerPage"
      v-on:goTo="changePage"
      :totalEntities="totalEntities"
      :entitiesPerPage="entitiesPerPage"
      :currentPage="currentPage"/>

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
      <small>{{ totalEntities }} result(s)</small>
    </div>
  </div>
  <EntityListTable
      @reorder="reorder"
      :entities="entities"
      :schema="schema"
      :loading="loading"/>

  <Pagination
      v-if="totalEntities > entitiesPerPage"
      v-on:goTo="changePage"
      :totalEntities="totalEntities"
      :entitiesPerPage="entitiesPerPage"
      :currentPage="currentPage"
  />
</template>

<script>
import Pagination from "./Pagination.vue";
import EntityListTable from "@/components/EntityListTable";
import SearchPanel from "./SearchPanel.vue";
import {api} from "@/api";

export default {
  components: {EntityListTable, Pagination, SearchPanel},
  name: "EntityList",
  props: ["schema"],
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
      this.getEntities({resetPage: true});
    },
    schema() {
      console.debug("Schema has changed?", this.schema)
      if (this.schema === undefined || this.schema === null) {
        console.debug("Oops, no valid schema")
        return
      }
      this.getEntities();
    }
  },
  methods: {
    async changePage(page) {
      this.currentPage = page;
      await this.getEntities();
    },
    async getEntities({resetPage = false} = {}) {
      console.debug("Getting entities");
      let _this = this;
      if (resetPage) {
        this.currentPage = 1;
      }
      this.loading = true;
      api.getEntities({
        schemaSlug: this.schema.slug,
        limit: this.entitiesPerPage,
        offset: this.offset,
        filters: this.filters,
        orderBy: this.orderBy,
        ascending: this.ascending,
      }).then(response => {
        console.debug("Got entities", response)
        _this.entities = response.entities;
        _this.totalEntities = response.total;
        _this.loading = false
      });

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
      loading: true
    };
  },
  mounted() {
    if (this.schema !== undefined && this.schema !== null) {
      this.getEntities();
    }
  }
};
</script>

