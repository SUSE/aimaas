<template>
  <h2>Create new schema</h2>
  <form class="my-3">
    <div class="mb-3">
      <TextInput
        v-model="name"
        label="Name of schema"
        :args="{ maxlength: 128, id: 'name' }"
      />
    </div>
    <div class="mb-3">
      <TextInput
        v-model="slug"
        label="Slug"
        :args="{ maxlength: 128, id: 'slug' }"
      />
      <div id="slugHelp" class="form-text">URL-friendly ID of schema</div>
    </div>
    <Checkbox
      v-model="this.reviewable"
      label="Require reviews for schema and entities changes"
      :args="{ id: 'reviewable' }"
    />
  </form>

  <h3>Attributes</h3>
  <form v-for="(attr, rowIndex) in attributeDefinitions" :key="rowIndex">
    <div class="row">
      <div class="col-lg-3">
        <label :for="`attrName${rowIndex}`">Attribute name</label>
        <TextInput
          v-model="this.attributeDefinitions[rowIndex].name"
          :args="{ id: `attrName${rowIndex}`, list: 'attributes' }"
        />
        <datalist id="attributes">
          <option
            v-for="(attr, index) in availableFieldNames"
            :key="index"
            :value="attr.name"
          >
            {{ `${attr.name} (${attr.type})` }}
          </option>
        </datalist>
      </div>

      <div class="col-lg-3">
        <Select
          label="Attribute type"
          v-model="this.attributeDefinitions[rowIndex].type"
          :options="
            Object.keys(ATTR_TYPES_NAMES).map((type) => {
              return { value: type, text: ATTR_TYPES_NAMES[type] };
            })
          "
          :args="{ id: `attrType${rowIndex}` }"
        />
      </div>

      <div v-if="this.attributeDefinitions[rowIndex].type == 'FK'" class="col">
        <Select
          label="Bind to schema"
          v-model="this.attributeDefinitions[rowIndex].bind_to_schema"
          :options="
            this.schemasToBind.map((schema) => {
              return { value: schema.id, text: schema.name };
            })
          "
          :args="{ id: `boundFK${rowIndex}` }"
        />
      </div>

      <div class="col-lg-3">
        <Textarea
          label="Description (optional)"
          v-model="this.attributeDefinitions[rowIndex].description"
          :args="{ id: `description${rowIndex}` }"
        />
      </div>
    </div>

    <div class="row">
      <div class="form">
        <div class="form-check form-check-inline">
          <Checkbox
            label="Key"
            v-model="this.attributeDefinitions[rowIndex].key"
            :args="{ id: `key${rowIndex}` }"
          />
        </div>
        <div class="form-check form-check-inline">
          <Checkbox
            label="Unique"
            v-model="this.attributeDefinitions[rowIndex].unique"
            :args="{ id: `unique${rowIndex}` }"
          />
        </div>
        <div class="form-check form-check-inline">
          <Checkbox
            label="Required"
            v-model="this.attributeDefinitions[rowIndex].required"
            :args="{ id: `required${rowIndex}` }"
          />
        </div>
        <div class="form-check form-check-inline">
          <Checkbox
            label="List"
            v-model="this.attributeDefinitions[rowIndex].list"
            :args="{ id: `list${rowIndex}` }"
          />
        </div>
      </div>
    </div>
    <div class="col">
      <button
        @click="this.attributeDefinitions.splice(rowIndex, 1)"
        type="button"
        class="btn btn-sm btn-outline-secondary"
      >
        Remove
      </button>
    </div>
  </form>
  <form class="mt-3">
    <button
      @click="
        this.attributeDefinitions.push({
          name: '',
          type: 'STR',
          key: false,
          unique: false,
          required: false,
          list: false,
          description: null,
          bind_to_schema: -1,
        })
      "
      type="button"
      class="btn btn-sm btn-primary"
    >
      Add attribute
    </button>
  </form>

  <button @click="sendData" type="button" class="mt-3 btn btn-outline-primary">
    Create schema
  </button>
</template>


<script>
import { api } from "../api";
import TextInput from "./inputs/TextInput.vue";
import Textarea from "./inputs/Textarea.vue";
import Checkbox from "./inputs/Checkbox.vue";
import Select from "./inputs/Select.vue";
import { ATTR_TYPES_NAMES } from "../utils";

export default {
  name: "SchemaCreate",
  components: { TextInput, Checkbox, Select, Textarea },
  data() {
    return {
      schemas: [],
      name: "",
      slug: "",
      attributeDefinitions: [],
      attributes: [],
      reviewable: false,
      ATTR_TYPES_NAMES,
    };
  },
  async mounted() {
    let response = await api.getAttributes();
    this.attributes = await response.json();
    response = await api.getSchemas();
    this.schemas = await response.json();
  },
  methods: {
    async sendData() {
      const json = {
        name: this.name,
        slug: this.slug,
        reviewable: this.reviewable,
        attributes: [],
      };
      for (let attrDef of this.attributeDefinitions) {
        if (attrDef.name == "") continue;
        json.attributes.push({
          ...attrDef,
        });
      }
      const response = await api.createSchema({ body: json });
      if (response.status == 200) {
        this.$router.push(`/${this.slug}`);
      }
    },
  },
  computed: {
    availableFieldNames() {
      const usedNames = this.attributeDefinitions.map(
        (attr_def) => attr_def.name
      );
      return this.attributes
        .filter((attr) => !usedNames.includes(attr.name))
        .sort((a, b) => (a.name > b.name ? 1 : -1));
    },
    schemasToBind() {
      return [{ id: -1, name: "<this new schema>" }, ...this.schemas];
    },
  },
};
</script>