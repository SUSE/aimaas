<template>
  <template v-if="asDropdown">
    <li class="nav-item dropdown">
      <a class="nav-link dropdown-toggle" href="#" id="nav-schema-dropdown" role="button"
         data-bs-toggle="dropdown" aria-expanded="false">
        <i class='eos-icons me-1'>namespace</i>
        Schema
      </a>
      <ul class="dropdown-menu" aria-labelledby="nav-schema-dropdown">
        <li v-if="loading">
          <div class="dropdown-item placeholder-wave">
            <span class="placeholder col-8"></span>
          </div>
        </li>
        <li v-for="schema in schemas" :key="schema.id">
          <router-link :to="{name: 'schema-view', params: {schemaSlug: schema.slug}}"
                       class="dropdown-item" :class="modelValue?.id === schema.id ? 'active': ''">
            {{ schema.name }}
          </router-link>
        </li>
        <li>
          <hr class="dropdown-divider">
        </li>
        <li>
          <RouterLink
              to="/createSchema"
              class="dropdown-item">
            <i class='eos-icons me-1'>add_circle</i>
            New
          </RouterLink>
        </li>
      </ul>
    </li>
  </template>
  <template v-else>
    <BaseLayout key="/"/>
    <div class="container">
      <SelectInput label="Filter:" v-model="listMode" :options="listOptions" @change="load"
                   :args="{id: 'mode'}"/>
      <template v-if="schemas && schemas.length > 0">
        <div class="list-group">
          <div class="list-group-item d-flex" v-for="schema in schemas" :key="schema.id">
            <div class="me-3">
              <input :disabled="schema.deleted" type="checkbox" :data-slug="schema.slug"
                     class="form-check-input" name="SchemaSelection"
                     :id="`select-${schema.slug}`" @change="onChange"/>
            </div>
            <div class="flex-grow-1">
              <router-link :to="{name: 'schema-view', params: {schemaSlug: schema.slug}}">
                {{ schema.name }}
              </router-link>
            </div>
          </div>
        </div>
        <div v-if="numSelected > 0 && listMode !== 'only-deleted'">
          <ConfirmButton btnClass="btn-outline-danger" :callback="onDelete">
            <template v-slot:label>
              <i class="eos-icons me-1">delete</i>
              Delete {{ numSelected }} schema(s)
            </template>
          </ConfirmButton>
        </div>
      </template>
      <div class="alert alert-info" v-else>
        No schemas defined.
        <RouterLink :to="{name: 'schema-new'}" v-if="listMode !== 'only-deleted'">
          Please define one now.
        </RouterLink>
      </div>
    </div>
  </template>
</template>

<script>
import BaseLayout from "@/components/layout/BaseLayout";
import ConfirmButton from "@/components/inputs/ConfirmButton";
import SelectInput from "@/components/inputs/SelectInput";

export default {
  name: "SchemaList",
  props: {
    modelValue: {
      required: false
    },
    asDropdown: {
      type: Boolean,
      default: false
    }
  },
  components: {SelectInput, BaseLayout, ConfirmButton},
  data: function () {
    return {
      schemas: null,
      loading: true,
      selected: [],
      listMode: "active",
      listOptions: [
        {
          value: "active",
          text: "Active"
        },
        {
          value: "all",
          text: "All"
        },
        {
          value: "only-deleted",
          text: "Only Deleted"
        }
      ],
      queryOptions: {
        active: {all: false, deletedOnly: false},
        all: {all: true, deletedOnly: false},
        "only-deleted": {all: false, deletedOnly: true},
      }
    }
  },
  created: function () {
    this.load();
  },
  computed: {
    numSelected() {
      return this.selected.length;
    }
  },
  methods: {
    onChange() {
      const elems = document.getElementsByName("SchemaSelection");
      this.selected = Array.prototype.filter.call(elems, e => e.checked).map(e => e.dataset.slug);
    },
    onDelete() {
      const promises = this.selected.map(slug => {
        this.$api.deleteSchema({slugOrId: slug})
      });
      Promise.all(promises).then(this.load)

    },
    load() {
      this.loading = true;
      this.$api.getSchemas(this.queryOptions[this.listMode]).then(data => {
        this.schemas = data;
        this.loading = false;
      });
    }
  }

};
</script>
