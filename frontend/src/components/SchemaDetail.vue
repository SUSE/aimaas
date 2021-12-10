<template>
  <BaseLayout>
    <template v-slot:additional_breadcrumbs>
      <li class="breadcrumb-item">{{ this.schema.name }}</li>
      <li class="breadcrumb-item active">Details</li>
    </template>
    <template v-slot:actions>
      <router-link
          :to="`/edit/${this.$route.params.schemaSlug}`"
          class="btn btn-primary ms-1"
          data-bs-toggle="tooltip"
          data-bs-placement="bottom"
          title="Edit schema structure">
        <i class="eos-icons">mode_edit</i>
        Edit
      </router-link>
    </template>
  </BaseLayout>
  <template v-if="this.schema">
    <div class="row">
      <div class="col">
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
    </div>
    <h3>Attributes</h3>
    <div class="table-responsive">
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
          <td v-if="attr.type != 'FK'">{{ this.ATTR_TYPES_NAMES[attr.type] }}</td>
          <td v-else>
            <RouterLink :to="`/${this.fkSchemas[attr.bind_to_schema].slug}`"
            >{{ this.ATTR_TYPES_NAMES[attr.type] }}
            </RouterLink>
          </td>

          <td class="text-center" v-if="attr.unique">
            <CheckIcon/>
          </td>
          <td class="text-center" v-else>
            <CircleXIcon/>
          </td>

          <td class="text-center" v-if="attr.required">
            <CheckIcon/>
          </td>
          <td class="text-center" v-else>
            <CircleXIcon/>
          </td>

          <td class="text-center" v-if="attr.key">
            <CheckIcon/>
          </td>
          <td class="text-center" v-else>
            <CircleXIcon/>
          </td>

          <td class="text-center" v-if="attr.list">
            <CheckIcon/>
          </td>
          <td class="text-center" v-else>
            <CircleXIcon/>
          </td>

          <td>{{ attr.description || "N/A" }}</td>
        </tr>
        </tbody>
      </table>
    </div>
  </template>

  <template v-else>Nothing to show</template>
</template>


<script>
import BaseLayout from "@/components/layout/BaseLayout.vue";
import CheckIcon from "./CheckIcon.vue";
import CircleXIcon from "./CircleXIcon.vue";
import {api} from "../api";
import {ATTR_TYPES_NAMES} from "../utils";


export default {
  name: "SchemaDetail",
  props: [],
  components: {BaseLayout, CheckIcon, CircleXIcon},
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
              await api.getSchema({slugOrId: attr.bind_to_schema})
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
      ATTR_TYPES_NAMES,
    };
  },
};
</script>