<template>
  <SearchPanel
      @search="setFiltersAndSearch"
      :key="schema?.slug"
      :filterable-fields="filterableFields"
      :operators="operators"
      :advanced-controls="advancedControls"/>
  <div class="d-flex align-items-center mt-1 gap-2">
    <div class="me-auto">
      <Pagination v-if="totalEntities > entitiesPerPage" v-on:goTo="changePage"
                  :total-items="totalEntities" :items-per-page="entitiesPerPage"
                  :currentPage="currentPage"/>
    </div>
    <div class="d-flex gap-2">
      <label for="entitiesLimit" class="me-1"><small>Page size</small></label>
      <div>
        <select v-model="entitiesPerPage" id="entitiesLimit" class="form-select form-select-sm"
                style="width: 5.5rem;" @change="getEntities({resetPage: true})">
          <option>10</option>
          <option>30</option>
          <option>50</option>
        </select>
      </div>
    </div>
    <small>{{ totalEntities }} result(s)</small>
  </div>

  <EntityListTable
      ref="selector"
      @reorder="reorder"
      @select="onSelection"
      :entities="entities"
      :selected="selected"
      :schema="schema"
      :loading="loading"
      :selectType="selectType"/>
  <div class="flex-grow-1 align-middle">
    <ConfirmButton v-if="numSelected > 0 && advancedControls" :callback="onDeletion"
                   btn-class="btn-outline-danger">
      <template v-slot:label>
        <i class="eos-icons me-1">delete</i>
        Delete {{ numSelected }} {{ numSelected == 1 ? 'entity' : 'entities' }}
      </template>
    </ConfirmButton>
  </div>
</template>

<script>
import ConfirmButton from "@/components/inputs/ConfirmButton";
import Pagination from "./layout/Pagination.vue";
import EntityListTable from "@/components/EntityListTable";
import SearchPanel from "./SearchPanel.vue";

export default {
  components: {EntityListTable, Pagination, SearchPanel, ConfirmButton},
  name: "EntityList",
  props: {
    schema: Object,
    selectType: {
      type: String,
      default: "many",
      validator(value) {
        return ['many', 'single', 'none'].includes(value);
      }
    },
    advancedControls: {
      type: Boolean,
      default: false
    }
  },
  computed: {
    offset() {
      return (this.currentPage - 1) * this.entitiesPerPage;
    },
    pages() {
      return Math.ceil(this.totalEntities / this.entitiesPerPage);
    },
    numSelected() {
      return this.selected.length;
    }
  },
  watch: {
    entitiesPerPage() {
      this.getEntities({resetPage: true});
    },
    schema() {
      if (!this.schema) {
        return
      }
      this.orderBy = 'name';
      this.ascending = true;
      this.getEntities({resetPage: true});
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
        this.selected = [];
      }
      this.loading = true;
      const response = await this.$api.getEntities({
        schemaSlug: this.schema.slug,
        limit: this.entitiesPerPage,
        offset: this.offset,
        filters: this.filters,
        orderBy: this.orderBy,
        ascending: this.ascending,
        meta: true
      });
      this.entities = response.entities;
      this.totalEntities = response.total;
      this.operators = response.meta.filter_fields.operators;
      this.filterableFields = response.meta.filter_fields.fields;
      this.loading = false;
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
    getSelected() {
      const selectedIds = this.$refs.selector.getSelected();
      return this.entities.filter(x => selectedIds.includes(x.id));
    },
    onSelection() {
      this.selected = this.$refs.selector.getSelected();
    },
    onDeletion() {
      const promises = this.selected.map(eId => {
        this.$api.deleteEntity({schemaSlug: this.schema.slug,
                               entityIdOrSlug: eId});
      });
      Promise.all(promises).then(() => this.getEntities({resetPage: true}));
    }
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
      loading: true,
      selected: []
    };
  }
};
</script>

