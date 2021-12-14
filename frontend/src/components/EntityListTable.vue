<template>
  <div v-if="!loading && entities.length > 0" class="table-responsive">
    <table class="table table-bordered table-hover">
      <thead class="table-light">
      <tr>
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
        <td v-for="field in displayFields" :key="field">
          <template v-if="field === 'name'">
            <RouterLink :to="{name: 'entity-view', params: {schemaSlug: schema.slug, entityIdOrSlug: e.slug }}">
              {{ e[field] }}
            </RouterLink>
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
const NON_DISPLAY_FIELDS = ['id', 'slug', 'deleted'];

export default {
  name: 'EntityListTable',
  props: ['entities', 'schema', 'loading'],
  emits: ['reorder'],
  updated() {
    if (this.previousSchema !== this.schemaSlug) {
      this.previousSchema = this.schemaSlug;
      this.ascending = true;
      this.orderBy = 'name';
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
  },
  data() {
    return {
      orderBy: 'name',
      ascending: true,
      previousSchema: '',
    };
  },
  methods: {
    orderByField(field) {
      if (this.orderBy === field) {
        this.ascending = !this.ascending;
      } else {
        this.orderBy = field;
        this.ascending = true;
      }
      this.$emit('reorder', {orderBy: this.orderBy, ascending: this.ascending})
    },
  },
};
</script>
