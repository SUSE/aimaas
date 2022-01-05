<template>
  <SearchPanel
      @search="setFiltersAndSearch"
      :key="schema?.slug"
      :filterable-fields="filterableFields"
      :operators="operators"
      :advanced-controls="advancedControls"/>
  <Pagination :total-items="totalEntities" v-model="currentPage" ref="paginator"
              @change="getEntities({resetPage: true})">
    <template v-slot:default>
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
  </Pagination>
</template>

<script>
import {computed} from "vue";

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
    pages: computed(() => this.$refs.paginator.pageCount),
    offset() {
      return (this.currentPage - 1) * this.$refs.paginator.pageSize;
    },
    numSelected() {
      return this.selected.length;
    }
  },
  watch: {
    currentPage(oldPage, newPage) {
      if (oldPage !== newPage) {
        this.getEntities({resetPage: false});
      }
    }
  },
  methods: {
    async onUpdate() {
      this.orderBy = 'name';
      this.ascending = true;
      await this.getEntities({resetPage: true});
    },
    async getEntities({resetPage = false} = {}) {
      if (resetPage) {
        this.currentPage = 1;
        this.selected = [];
      }
      this.loading = true;
      if (!this.schema) {
        return;
      }
      const response = await this.$api.getEntities({
        schemaSlug: this.schema.slug,
        limit: this.$refs.paginator.pageSize,
        offset: this.offset,
        filters: this.filters,
        orderBy: this.orderBy,
        ascending: this.ascending,
        meta: true
      });
      this.entities = response.entities;
      this.totalEntities = response.total;
      if (response.meta) {
        this.operators = response.meta.filter_fields.operators;
        this.filterableFields = response.meta.filter_fields.fields;
      }
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
        this.$api.deleteEntity({
          schemaSlug: this.schema.slug,
          entityIdOrSlug: eId
        });
      });
      Promise.all(promises).then(() => this.getEntities({resetPage: true}));
    }
  },
  async mounted() {
    await this.getEntities({resetPage: true}).then(() => null);
  },
  created() {
    this.$watch("schema", this.onUpdate);
  },
  data() {
    return {
      entities: [],
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

