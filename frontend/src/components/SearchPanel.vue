<template>
  <div class="d-flex input-group mb-1">
    <input v-model="searchQuery" type="text" class="form-control" placeholder="search by name"
           :autofocus="true" @keyup.enter="$emit('search', this.filters)" id="entity-name-search"/>
    <button @click="$emit('search', this.filters)" class="btn btn-primary px-3"
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
        <div class="row border-bottom border-light pb-1 mb-1" :key="rowIndex"
             v-for="(row, rowIndex) in this.filterRows">
          <!-- SELECT FILTER FIELD -->
          <div class="col-md-4">
            <label :for="`fieldSelect${rowIndex}`">Field</label>
            <select class="form-control" :id="`fieldSelect${rowIndex}`"
                    v-model="this.filterRows[rowIndex].field">
              <option v-for="(field, index) in Object.keys(this.filterableFields)" :key="index">
                {{ field }}
              </option>
            </select>
          </div>

          <!-- SELECT FILTER OPERATOR -->
          <div class="col-md-3">
            <label :for="`operatorSelect${rowIndex}`">Operator</label>
            <select class="form-control" :id="`operatorSelect${rowIndex}`"
                    v-model="this.filterRows[rowIndex].operator"
                    :disabled="!this.filterRows[rowIndex].field">
              <option v-for="(field, index) in getFiltersForRow(rowIndex)" :key="index"
                      :value="field">
                {{ OPERATOR_DESCRIPTION_MAP[field] }}
              </option>
            </select>
          </div>

          <!-- INPUT FILTER VALUE -->
          <div class="col-md-4">
            <label :for="`filterValue${rowIndex}`">Value</label>
            <input :type="TYPE_INPUT_MAP[this.getFieldTypeForRow(rowIndex)]?.type || 'text'"
                   :class="TYPE_INPUT_MAP[this.getFieldTypeForRow(rowIndex)]?.type ===
                           'checkbox' ? 'form-check-input' : 'form-control'"
                   :id="`filterValue${rowIndex}`" :disabled="!this.filterRows[rowIndex].field"
                   v-model="this.filterRows[rowIndex].value"/>
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
        <button @click="$emit('search', this.filters)" class="btn btn-primary flex-grow-1 ms-1"
                type="button" data-bs-toggle="tooltip" title="Search">
          <i class='eos-icons me-1'>search</i>
          Search
        </button>
      </div>

    </div>
  </div>
</template>

<script>
const OPERATOR_DESCRIPTION_MAP = {
  eq: "equals to",
  ne: "not equal to",
  lt: "less than",
  le: "less than or equal to",
  gt: "greater than",
  ge: "greater than or equal",
  contains: "contains substring",
  regexp: "matches regular expression",
  starts: "starts with substring",
};

const TYPE_INPUT_MAP = {
  str: {type: "text"},
  datetime: {type: "datetime-local"},
  date: {type: "date"},
  int: {type: "number", args: {step: 1}},
  float: {type: "number"},
  bool: {type: "checkbox"},
};

export default {
  name: "SearchPanel",
  props: ["filterableFields", "operators"],
  emits: ["search"],
  computed: {
    filters() {
      const params = {};
      if (this.searchQuery !== "") {
        params["name.contains"] = this.searchQuery;
      }
      this.filterRows.map((row) => {
        if (row.field == null || row.operator == null || row.value == null)
          return;
        params[`${row.field}.${row.operator}`] = row.value;
      });
      return params;
    },
  },
  methods: {
    addFilter() {
      this.filterRows.push({field: null, operator: null, value: null});
    },
    clearFilters() {
      this.filterRows.splice(0, this.filterRows.length);
      this.searchQuery = "";
    },
    getFieldTypeForRow(rowIndex) {
      const fieldName = this.filterRows[rowIndex].field;
      try {
        return this.filterableFields[fieldName].type
      } catch {
        return undefined;
      }
    },
    getFiltersForRow(rowIndex) {
      const fieldType = this.getFieldTypeForRow(rowIndex);
      return this.operators[fieldType] || [];
    },
    removeFilter(rowIndex) {
      this.filterRows.splice(rowIndex, 1);
    },
  },
  data() {
    return {
      filterRows: [],
      searchQuery: "",
      OPERATOR_DESCRIPTION_MAP,
      TYPE_INPUT_MAP,
    };
  },
};
</script>
