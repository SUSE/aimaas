<template>
  <div class="accordion" id="filtersAccordion">
    <div class="accordion-item">
      <h2 class="accordion-header">
        <button
          class="accordion-button"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#collapseOne"
        >
          Search filters
        </button>
      </h2>
      <div
        id="collapseOne"
        class="accordion-collapse collapse"
        data-bs-parent="#filtersAccordion"
      >
        <div class="accordion-body">
          <form class="row row-cols-lg-auto g-3 align-items-center">
            <div
              class="row"
              v-for="(row, rowIndex) in this.filterRows"
              :key="rowIndex"
            >
              <!-- SELECT FILTER FIELD -->
              <div class="col-4">
                <label :for="`fieldSelect${rowIndex}`">Field</label>
                <select
                  class="form-control"
                  :id="`fieldSelect${rowIndex}`"
                  v-model="this.filterRows[rowIndex].field"
                >
                  <option
                    v-for="(field, index) in Object.keys(this.filterableFields)"
                    :key="index"
                  >
                    {{ field }}
                  </option>
                </select>
              </div>

              <!-- SELECT FILTER OPERATOR -->
              <div v-if="this.filterRows[rowIndex].field != null" class="col">
                <label :for="`operatorSelect${rowIndex}`">Operator</label>
                <select
                  class="form-control mb-2 mr-sm-2"
                  :id="`operatorSelect${rowIndex}`"
                  v-model="this.filterRows[rowIndex].operator"
                >
                  <option
                    v-for="(field, index) in getFiltersForRow(rowIndex)"
                    :key="index"
                    :value="field"
                  >
                    {{ OPERATOR_DESCRIPTION_MAP[field] }}
                  </option>
                </select>
              </div>
              <div v-else class="col">
                <label :for="`operatorSelect${rowIndex}`">Operator</label>
                <input
                  :id="`operatorSelect${rowIndex}`"
                  class="form-control"
                  disabled
                />
              </div>

              <!-- INPUT FILTER VALUE -->
              <div v-if="this.filterRows[rowIndex].field != null" class="col">
                <label :for="`filterValue${rowIndex}`">Value</label>
                <input
                  :type="TYPE_INPUT_MAP[this.getFieldTypeForRow(rowIndex)].type"
                  :class="
                    TYPE_INPUT_MAP[this.getFieldTypeForRow(rowIndex)].type ==
                    'checkbox'
                      ? 'form-check-input'
                      : 'form-control'
                  "
                  :id="`filterValue${rowIndex}`"
                  v-model="this.filterRows[rowIndex].value"
                />
              </div>
              <div v-else class="col">
                <label :for="`filterValue${rowIndex}`">Value</label>
                <input
                  :id="`filterValue${rowIndex}`"
                  class="form-control"
                  disabled
                />
              </div>

              <!-- REMOVE FILTER -->
              <div class="col-1">
                <button
                  @click="this.removeFilter(rowIndex)"
                  type="button"
                  class="btn-close mt-4"
                ></button>
              </div>

            </div>
          </form>

          <button
            type="button"
            class="btn btn-sm btn-primary ms-1 mt-3"
            @click="
              this.filterRows.push({
                field: null,
                operator: null,
                value: null,
              })
            "
          >
            Add filter
          </button>
        </div>
      </div>
    </div>
  </div>

  <div class="input-group mb-3 mt-3">
    <input
      v-model="searchQuery"
      type="text"
      class="form-control"
      placeholder="search by entity name"
      style="background-color: #f5f5f5"
      :autofocus="true"
      @keyup.enter="$emit('search', this.filters)"
    />
    <button
      @click="$emit('search', this.filters)"
      class="btn btn-outline-primary"
      type="button"
      id="button-addon2"
    >
      Search
    </button>
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
  str: { type: "text" },
  datetime: { type: "datetime-local" },
  date: { type: "date" },
  int: { type: "number", args: { step: 1 } },
  float: { type: "number" },
  bool: { type: "checkbox" },
};

export default {
  name: "SearchPanel",
  props: ["filterableFields", "operators"],
  emits: ["search"],
  computed: {
    filters() {
      const params = {};
      if (this.searchQuery != "") {
        params["name.contains"] = this.searchQuery;
      }
      this.filterRows.map((row) => {
        if (row.field == null || row.operator == null || row.value == null)
          return;
        params[`${row.field}.${row.operator}`]=  row.value;
      });
      return params;
    },
  },
  methods: {
    getFieldTypeForRow(rowIndex) {
      const fieldName = this.filterRows[rowIndex].field;
      return this.filterableFields[fieldName].type;
    },
    getFiltersForRow(rowIndex) {
      const fieldType = this.getFieldTypeForRow(rowIndex);
      return this.operators[fieldType];
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
