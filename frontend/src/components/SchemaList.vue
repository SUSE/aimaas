<template>
  <li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle" href="#" id="nav-schema-dropdown" role="button"
       data-bs-toggle="dropdown" aria-expanded="false">
      {{ title }}
    </a>
    <ul class="dropdown-menu" aria-labelledby="nav-schema-dropdown">
      <li v-if="loading">
        <div class="dropdown-item placeholder-wave">
          <span class="placeholder col-8"></span>
        </div>
      </li>
      <li v-for="schema in schemas" :key="schema.id">
        <button type="button" class="dropdown-item" :class="modelValue === schema ? 'active': ''"
           v-on:click="selectSchema" :value="schema.id">
          {{ schema.name }}
        </button>
      </li>
      <li>
        <hr class="dropdown-divider">
      </li>
      <li>
        <RouterLink
            to="/createSchema"
            class="dropdown-item">
          <i class='eos-icons'>add_circle</i>
          New
        </RouterLink>
      </li>
    </ul>
  </li>
</template>

<script>
import {api} from "@/api";

export default {
  name: "SchemaList",
  props: ["modelValue"],
  emits: ["update:modelValue"],
  data: function () {
    return {
      schemas: null,
      loading: true
    }
  },

  components: {},
  computed: {
    title() {
      if (this.modelValue !== undefined && this.modelValue !== null) {
        return `Schema: ${this.modelValue.name}`;
      }
      return "Schema";
    }
  },
  mounted: function () {
    console.debug("Route", this.$route, this.$router)
    this.load();
  },
  methods: {
    async load() {
      this.loading = true;
      this.schemas = await api.getSchemas();
      console.debug("Schemas", this.schemas);
      this.loading = false;
    },
    getSchemaForId(id) {
      if (!this.schemas) {
        return null;
      }
      for (let schema of this.schemas) {
        if (schema.id == id) {
          return schema;
        }
      }
    },
    selectSchema(event) {
      event.preventDefault();
      console.debug("Event", event, event.target.value);
      this.$emit("update:modelValue", this.getSchemaForId(event.target.value));
    }
  }

};
</script>
