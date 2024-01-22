<template>
  <div v-if="!loading && entities.length > 0" class="table-responsive">
    <table class="table table-bordered table-hover">
      <thead class="table-light">
      <tr>
        <th v-if="showSelectors"></th>
        <th
          @click="orderByField(field.name)"
          v-for="field in displayFieldsWithDescriptions"
          :key="field.name"
          :title="field.description"
        >
          {{ field.name }}
          <template v-if="field.name === orderBy"
          ><span v-if="ascending">↑</span
          ><span v-else>↓</span></template
          >
        </th>
      </tr>
      </thead>
      <tbody>
      <tr v-for="e in entities" :key="e.id" :class="{'table-light': e.deleted}">
        <td v-if="showSelectors">
          <input :type="inputType" class="form-check-input" name="EntitySelection" :value="e.id"
                 @change="$emit('select')" :checked="selected.includes(e.id)" />
        </td>
        <td v-for="field in displayFieldsWithDescriptions" :key="field.name">
          <template v-if="field.name === 'name'">
            <RouterLink
                :to="{name: 'entity-view', params: {schemaSlug: schema.slug, entitySlug: e.slug }}">
              {{ e[field.name] }}
            </RouterLink>
            <i class="eos-icons float-end text-muted" v-if="e.deleted" data-bs-toggle="tooltip"
               title="Entity is deleted">
              delete
            </i>
          </template>
          <template v-else-if="field.name in fkFields">
            <RefEntityList v-if="listFields.includes(field.name)" :entity-ids="e[field.name]"
                           :schema-slug="fkFields[field.name]"/>
            <RefEntity v-else :entity-id="e[field.name]" :schema-slug="fkFields[field.name]"/>
          </template>
          <template v-else-if="listFields.includes(field.name)">
            <div class="d-flex flex-wrap gap-3">
              <div v-for="(value, idx) in e[field.name]" :key="`${field.name}-${idx}`">
                {{ value }}
              </div>
            </div>
          </template>
          <template v-else-if="field.name in dateFields">
            {{ formatDT(field.name, e[field.name]) }}
          </template>
          <template v-else>
            {{ e[field.name] }}
          </template>
        </td>
      </tr>
      </tbody>
    </table>
  </div>
  <div v-else-if="loading" class="d-flex justify-content-center py-4">
    <div class="spinner-border" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
  </div>
  <div v-else class="alert alert-info">
    No entities to show
  </div>
</template>

<script>
import RefEntity from "@/components/RefEntity";
import RefEntityList from "@/components/RefEntityList";

const NON_DISPLAY_FIELDS = ['id', 'slug', 'deleted'];

export default {
  name: 'EntityListTable',
  props: ['entities', 'schema', 'loading', 'selectType', 'selected'],
  inject: ["availableSchemas"],
  components: {RefEntity, RefEntityList},
  emits: ['reorder', 'select'],
  async created() {
    this.datetimeFormat = new Intl.DateTimeFormat(
        navigator.language,
        {dateStyle: "medium", timeStyle: "short"}
    );
    this.dateFormat = new Intl.DateTimeFormat(navigator.language, {dateStyle: "medium"});
  },
  async updated() {
    if (this.previousSchema !== this.schema) {
      this.previousSchema = this.schema;
      this.ascending = true;
      this.orderBy = 'name';
    }
  },
  computed: {
    displayFieldsWithDescriptions() {
      if (this.entities.length < 1) {
        return [];
      }

      let fields = Object.keys(this.entities[0]).filter(
        (x) => !NON_DISPLAY_FIELDS.includes(x)
      );

      fields = fields.sort((a, b) => (a > b ? 1 : -1));

      const nameIdx = fields.indexOf('name');
      fields.splice(nameIdx, 1);
      fields.unshift('name');
      
      const fieldsWithDescriptions = fields.map((field) => {
        let attribute = (this.schema?.attributes || []).find(attr => attr.name === field)
        return {
          name: field, // using attribute?.name causes display errors at runtime
          description: attribute?.description
        };
      });
      
      return fieldsWithDescriptions;
    },
    fkFields() {
      const fkSchemas = {};
      for (const attr of (this.schema?.attributes || [])) {
        if (attr.type === 'FK') {
          fkSchemas[attr.name] = this.refSchemaSlug[attr.bound_schema_id];
        }
      }
      return fkSchemas;
    },
    listFields() {
      return (this.schema?.attributes || []).filter(a => a.list).map(a => a.name);
    },
    dateFields() {
      const fields = {};
      for (let a of (this.schema?.attributes || []).filter(a => ['DATE', 'DT'].includes(a.type))) {
        fields[a.name] = a.type;
      }
      return fields;
    },
    inputType() {
      if (this.selectType === "many") {
        return "checkbox";
      } else if (this.selectType === "single") {
        return "radio";
      } else {
        return "hidden";
      }
    },
    showSelectors() {
      return this.inputType !== "hidden";
    },
    refSchemaSlug() {
      const sMap = {};
      for (const schema of this.availableSchemas) {
        sMap[schema.id] = schema.slug;
      }
      return sMap;
    }
  },
  data() {
    return {
      orderBy: 'name',
      ascending: true,
      previousSchema: null
    };
  }
  ,
  methods: {
    getSelected() {
      const elem = document.getElementsByName("EntitySelection");
      let s = [];
      for (let e of elem) {
        if (!e.checked) {
          continue;
        }
        s.push(parseInt(e.value));
      }
      return s;
    },
    orderByField(field) {
      if (this.listFields.includes(field)) {
        return;
      }
      if (this.orderBy === field) {
        this.ascending = !this.ascending;
      } else {
        this.orderBy = field;
        this.ascending = true;
      }
      this.$emit('reorder', {orderBy: this.orderBy, ascending: this.ascending})
    },
    formatDT(field, value) {
      if (!value) {
        return null;
      }
      const dvalue = new Date(value);
      if (this.dateFields[field] === "DATE") {
        return this.dateFormat.format(dvalue);
      }
      return this.datetimeFormat.format(dvalue);
    }
  },
}
;
</script>
