<template>
  <SearchPanel
      ref="searchpanel"
      @search="setFiltersAndSearch"
      :key="schema?.slug"
      :schema="schema"
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
      <div class="flex-grow-1 align-middle d-flex gap-3" id="selected-actions">
        <template v-if="numSelected > 0 && advancedControls">
          <small class="align-self-end">
            {{numSelected}} {{ entityPluralized }} selected
          </small>
          <ConfirmButton :callback="onDeletion"
                         btn-class="btn-outline-danger"
                         v-if="$refs?.searchpanel?.listMode !== 'deleted'">
            <template v-slot:label>
              <i class="eos-icons me-1">delete</i>
              <span>Delete</span>
            </template>
          </ConfirmButton>
          <ConfirmButton :callback="onRestoration"
                         btn-class="btn-outline-primary"
                         v-if="$refs?.searchpanel?.listMode !== 'active'">
            <template v-slot:label>
              <i class="eos-icons me-1">restore_from_trash</i>
              <span>Restore</span>
            </template>
          </ConfirmButton>
          <RouterLink class="btn btn-outline-primary"
                      :to="{name: 'bulk-edit', query: {entity: selected}}">
            <i class="eos-icons me-1">edit</i>
            <span>Edit</span>
          </RouterLink>
        </template>
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
    pages: computed(() => {
      try {
        return this.$refs.paginator.pageCount;
      } catch (e) {
        return 0;
      }
    }),
    numSelected() {
      return this.selected.length;
    },
    entityPluralized(){
      return this.numSelected === 1 ? 'entity' : 'entities'
    }
  },
  watch: {
    currentPage(oldPage, newPage) {
      if (oldPage !== newPage) {
        this.getEntities({resetPage: false});
      }
    },
    'schema': {
      async handler(newValue, oldValue) {
        try {
          if (newValue !== oldValue) {
            await this.onUpdate();
          }
        } catch (e) {
          console.error(e)
        }
      },
      immediate: true
    }
  },
  methods: {
    async onUpdate() {
      this.orderBy = 'name';
      this.ascending = true;
      await this.getEntities({resetPage: true});
    },
    async getEntities({resetPage = false} = {}) {
      this.selected.length = 0;

      if (resetPage) {
        this.currentPage = 1;
      }
      this.loading = true;
      if (!this.schema) {
        return;
      }
      const response = await this.$api.getEntities({
        schemaSlug: this.schema.slug,
        size: this.$refs.paginator?.pageSize || 10,
        page: this.currentPage,
        filters: this.filters,
        orderBy: this.orderBy,
        ascending: this.ascending,
      });
      this.entities = response.items;
      this.totalEntities = response.total;
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
    },
    onRestoration() {
      const promises = this.selected.map(eId => {
        this.$api.restoreEntity({
          schemaSlug: this.schema.slug,
          entityIdOrSlug: eId
        });
      });
      Promise.all(promises).then(() => this.getEntities({resetPage: true}));
    }
  },
  data() {
    return {
      entities: [],
      totalEntities: 0,
      currentPage: 1,
      filters: {},
      orderBy: "name",
      ascending: true,
      loading: true,
      selected: []
    };
  }
};
</script>
