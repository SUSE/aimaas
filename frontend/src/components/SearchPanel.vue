<template>
  <div class="d-flex input-group mb-1">
    <input v-model="searchQuery" type="text" class="form-control" placeholder="search by name"
           :autofocus="true" @keyup.enter="$emit('search', this.filterParams)"
           id="entity-name-search"/>
    <template v-if="advancedControls">
      <select class="form-select flex-grow-0" style="width: 10rem;" data-bs-toggle="tooltip"
              title="Entity state" v-model="listMode">
        <option>active</option>
        <option>deleted</option>
        <option>all</option>
      </select>
      <input type="checkbox" class="btn-check" id="allValues" v-model="allValues"
             autocomplete="off">
      <label for="allValues" class="btn" :class="allValues? 'btn-primary' : 'btn-light'"
             data-bs-toggle="tooltip" title="Show all attribute values">
        <i class="eos-icons">view_column</i>
      </label>
    </template>

    <button @click="$emit('search', this.filterParams)" class="btn btn-primary px-3"
            type="button" data-bs-toggle="tooltip" title="Search">
      <i class='eos-icons'>search</i>
    </button>
    <button class="btn btn-dark px-3" type="button" data-bs-toggle="collapse"
            data-bs-target="#collapsed-filters" aria-expanded="false"
            aria-controls="collapsed-filters" title="Click to expand more filter options">
      <i class="eos-icons">more_vert</i>
    </button>
  </div>
  <div id="collapsed-filters" class="collapse">
    <div class="card">
      <div class="card-body">
        <div v-if="advancedControls" class="row border-bottom border-light pb-1 mb-1">
          Goo!
        </div>
        <div class="row border-bottom border-light pb-1 mb-1 align-items-end" :key="rowIndex"
             v-for="(row, rowIndex) in this.filters">
          <!-- SELECT FILTER FIELD -->
          <div class="col-md-4">
            <SelectInput label="Field" :args="{id: `fieldSelect${rowIndex}`}"
                         :options="fieldOptions" :vertical="true" v-model="row.field"
                         @change="updateRow(row)"/>
          </div>

          <!-- SELECT FILTER OPERATOR -->
          <div class="col-md-3">
            <SelectInput v-model="row.operator" label="Operator"
                         :args="{id: `operatorSelect${rowIndex}`, disabled: !row.field}"
                         :vertical="true" :options="row.operatorOptions"/>
          </div>

          <!-- INPUT FILTER VALUE -->
          <div class="col-md-4">
            <component :is="row.component" v-model="row.value" label="Value" :vertical="true"
                       :disabled="!row.field"
                       :args="{id: `filterValue${rowIndex}`, disabled: !row.field}"/>
          </div>

          <!-- REMOVE FILTER -->
          <div class="col-md-1 d-flex">
            <button @click="this.removeFilter(rowIndex)" type="button"
                    class="btn align-self-end mb-1" data-bs-togle="tooltip" title="Remove filter">
              <i class="eos-icons">remove_circle</i>
            </button>
          </div>

        </div>
      </div>
      <div class="card-body d-flex">
        <button type="button" class="btn btn-outline-secondary flex-grow-1 me-1"
                @click="addFilter">
          <i class="eos-icons me-1">add_circle</i>
          Add filter
        </button>
        <button type="button" class="btn btn-outline-secondary flex-grow-1 mx-1"
                @click="clearFilters">
          <i class="eos-icons me-1">backspace</i>
          Clear filters
        </button>
        <button @click="$emit('search', this.filterParams)" class="btn btn-primary flex-grow-1 ms-1"
                type="button" data-bs-toggle="tooltip" title="Search">
          <i class='eos-icons me-1'>search</i>
          Search
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import {shallowRef} from "vue";
import {OPERATOR_DESCRIPTION_MAP, TYPE_INPUT_MAP} from "@/utils";
import IntegerInput from "@/components/inputs/IntegerInput.vue";
import FloatInput from "@/components/inputs/FloatInput.vue";
import TextInput from "@/components/inputs/TextInput.vue";
import Checkbox from "@/components/inputs/Checkbox.vue";
import DateTime from "@/components/inputs/DateTime.vue";
import DateInput from "@/components/inputs/DateInput.vue";
import SelectInput from "@/components/inputs/SelectInput.vue";

export default {
  name: "SearchPanel",
  props: ["filterableFields", "operators", "advancedControls"],
  components: {TextInput, Checkbox, DateTime, DateInput, IntegerInput, FloatInput, SelectInput},
  emits: ["search"],
  computed: {
    filterParams() {
      const params = {
        all_fields: this.allValues
      };
      if (this.listMode === 'deleted') {
        params.deleted_only = true;
      } else if (this.listMode === 'all') {
        params.all = true;
      }
      if (this.searchQuery !== "") {
        params["name.contains"] = this.searchQuery;
      }
      this.filters.map((row) => {
        if (row.field == null || row.operator == null || row.value == null)
          return;
        params[`${row.field}.${row.operator}`] = row.value;
      });
      return params;
    },
    fieldOptions() {
      let r = Object.keys(this.filterableFields).map(x => {
        return {value: x}
      });
      r.unshift({value: '', text: '-- select one --'})
      return r;
    }
  },
  methods: {
    addFilter() {
      this.filters.push({
        field: null,
        operator: null,
        value: null,
        operatorOptions: [],
        component: shallowRef(TextInput)
      });
    },
    clearFilters() {
      this.filters.splice(0, this.filters.length);
      this.searchQuery = "";
    },
    updateRow(row) {
      row.operatorOptions = this.getFiltersForRow(row);
      row.component = this.getComponentForRow(row);
    },
    getComponentForRow(row) {
      if (!row.field) {
        return null;
      }
      try {
        const fieldType = this.filterableFields[row.field].type.toUpperCase();
        return TYPE_INPUT_MAP[fieldType];
      } catch (e) {
        console.error(e);
        return null;
      }
    },
    getFiltersForRow(row) {
      if (!row || !row.field) {
        return [];
      }

      const fieldType = this.filterableFields[row.field]?.type;
      if (fieldType) {
        return (this.operators[fieldType] || []).map(o => {
          return {value: o, text: OPERATOR_DESCRIPTION_MAP[o]};
        });
      }
      return [];
    },
    removeFilter(rowIndex) {
      this.filters.splice(rowIndex, 1);
    },
  },
  data() {
    return {
      filters: [],
      searchQuery: "",
      allValues: false,
      listMode: 'active',
      OPERATOR_DESCRIPTION_MAP,
      TYPE_INPUT_MAP,
    };
  },
};
</script>
