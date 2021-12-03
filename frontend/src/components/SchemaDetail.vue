<template>
  <template v-if="this.schema">
    <div class="row">
      <div class="col">
        <h2>Schema {{ this.schema.name }}</h2>
        <p>
          <small>{{ this.schema.slug }}</small>
        </p>
        <p>
          <span
            v-if="this.schema.reviewable"
            class="badge rounded-pill bg-primary"
            >Reviewable</span
          >
          <span
            v-if="this.schema.deleted"
            class="ms-1 badge rounded-pill bg-warning text-dark"
            >Deleted</span
          >
        </p>
      </div>
      <div class="col-lg-2">
        <router-link
          :to="`/edit/${this.$route.params.schemaSlug}`"
          class="btn btn-sm btn-primary mt-3"
          style="text-decoration: none"
          >Edit schema</router-link
        >
      </div>
    </div>
    <h3>Attributes</h3>
    <table class="table table-bordered">
      <thead class="table-light">
        <tr>
          <th>Name</th>
          <th>Type</th>
          <th>Unique</th>
          <th>Required</th>
          <th>Key</th>
          <th>List</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="attr in this.schema.attributes" :key="attr.name">
          <td>{{ attr.name }}</td>
          <td v-if="attr.type != 'FK'">{{ this.ATTR_TYPES[attr.type] }}</td>
          <td v-else>
            <RouterLink :to="`/${this.fkSchemas[attr.bind_to_schema].slug}`"
              >{{ this.ATTR_TYPES[attr.type] }}
            </RouterLink>
          </td>

          <td class="text-center" v-if="attr.unique"><CheckIcon /></td>
          <td class="text-center" v-else><CircleXIcon /></td>

          <td class="text-center" v-if="attr.required"><CheckIcon /></td>
          <td class="text-center" v-else><CircleXIcon /></td>

          <td class="text-center" v-if="attr.key"><CheckIcon /></td>
          <td class="text-center" v-else><CircleXIcon /></td>

          <td class="text-center" v-if="attr.list"><CheckIcon /></td>
          <td class="text-center" v-else><CircleXIcon /></td>

          <td>{{ attr.description || "N/A" }}</td>
        </tr>
      </tbody>
    </table>
  </template>

  <template v-else>Nothing to show</template>
</template>


<script>
import CheckIcon from "./CheckIcon.vue";
import CircleXIcon from "./CircleXIcon.vue";
import { api } from "../api";

const ATTR_TYPES = {
  STR: "string",
  BOOL: "boolean",
  INT: "integer",
  FLOAT: "float",
  FK: "reference",
  DT: "datetime",
  DATE: "date",
};

export default {
  name: "SchemaDetail",
  props: [],
  components: { CheckIcon, CircleXIcon },
  watch: {
    $route: {
      handler: "onMount",
      immediate: true, // runs immediately with mount() instead of calling method on mount hook
    },
  },
  methods: {
    async onMount() {
      const response = await api.getSchema({
        slugOrId: this.$route.params.schemaSlug,
      });
      const schema = await response.json();

      for (const attr of schema.attributes) {
        if (attr.type == "FK" && !(attr.bind_to_schema in this.fkSchemas)) {
          this.fkSchemas[attr.bind_to_schema] = await (
            await api.getSchema({ slugOrId: attr.bind_to_schema })
          ).json();
        }
      }
      this.schema = schema;
    },
  },
  computed: {},
  data() {
    return {
      schema: null,
      fkSchemas: {},
      ATTR_TYPES,
    };
  },
};
</script>