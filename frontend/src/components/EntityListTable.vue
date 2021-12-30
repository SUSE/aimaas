<template>
  <div v-if="!loading && entities.length > 0" class="table-responsive">
    <table class="table table-bordered table-hover">
      <thead class="table-light">
      <tr>
        <th v-if="showSelectors"></th>
        <th
            @click="orderByField(field)"
            v-for="field in displayFields"
            :key="field"
        >
          {{ field }}
          <template v-if="field === orderBy"
          ><span v-if="ascending">↑</span
          ><span v-else>↓</span></template
          >
        </th>
      </tr>
      </thead>
      <tbody>
      <tr v-for="e in entities" :key="e.id">
        <td v-if="showSelectors">
          <input :type="inputType" class="form-check-input" name="EntitySelection" :value="e.id"
                 @change="$emit('select')" :checked="selected.includes(e.id)"
                 :disabled="e.deleted"/>
        </td>
        <td v-for="field in displayFields" :key="field">
          <template v-if="field === 'name'">
            <RouterLink
                :to="{name: 'entity-view', params: {schemaSlug: schema.slug, entitySlug: e.slug }}">
              {{ e[field] }}
            </RouterLink>
          </template>
          <template v-else-if="field in fkFields">
            <RefEntityList v-if="listFields.includes(field)" :entity-ids="e[field]"
                           :schema-slug="fkFields[field]"/>
            <RefEntity v-else :entity-id="e[field]" :schema-slug="fkFields[field]"/>
          </template>
          <template v-else-if="listFields.includes(field)">
            <div class="d-flex flex-wrap gap-3">
              <div v-for="(value, idx) in e[field]" :key="`${field}-${idx}`">
                {{ value }}
              </div>
            </div>
          </template>
          <template v-else>
            {{ e[field] }}
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
  updated() {
    if (this.previousSchema !== this.schema) {
      this.previousSchema = this.schema;
      this.ascending = true;
      this.orderBy = 'name';
      this.$api.getSchema({slugOrId: this.schema.slug}).then(x => {
        this.schemaDetails = x;
      });
    }
  },
  computed: {
    displayFields() {
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
      return fields;
    },
    fkFields() {
      const fkSchemas = {};
      for (const attr of (this.schemaDetails?.attributes || [])) {
        if (attr.type === 'FK') {
          fkSchemas[attr.name] = this.refSchemaSlug[attr.bind_to_schema];
        }
      }
      return fkSchemas;
    },
    listFields() {
      return (this.schemaDetails?.attributes || []).filter(a => a.list).map(a => a.name);
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
      previousSchema: null,
      schemaDetails: null
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
    }
    ,
    orderByField(field) {
      if (this.listFields.includes(field) || field in this.fkFields) {
        return;
      }
      if (this.orderBy === field) {
        this.ascending = !this.ascending;
      } else {
        this.orderBy = field;
        this.ascending = true;
      }
      this.$emit('reorder', {orderBy: this.orderBy, ascending: this.ascending})
    }
    ,
  }
  ,
}
;
</script>
