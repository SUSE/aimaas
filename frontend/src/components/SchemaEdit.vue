<template>
  <h2>Edit schema</h2>

  <form v-if="schema">
    <div class="mb-3">
      <TextInput label="Name of schema" v-model="name" :args="{ id: 'name' }" />
    </div>
    <div class="mb-3">
      <TextInput label="Slug" v-model="slug" :args="{ id: 'slug' }" />
      <div id="slugHelp" class="form-text">URL-friendly ID of schema</div>
    </div>

    <Checkbox
      label="Require reviews for schema and entities changes"
      v-model="reviewable"
      :args="{ id: 'reviewable', class: 'mb-3' }"
    />
  </form>
  <h3>Attributes</h3>
  <div v-if="schema">
    <EditInitialAttributes
      ref="initial"
      :schemas="schemas"
      :initialAttributes="clone(schema.attributes)"
      :availableFieldNames="availableFieldNames"
    />
    <AddNewAttributes
      ref="new"
      :schemas="schemas"
      :availableFieldNames="availableFieldNames"
    />
  </div>
  <button
    @click="sendData"
    type="button"
    class="mt-3 mb-3 btn btn-outline-primary"
  >
    Update schema
  </button>
</template>

<script>
import { api } from "../api";
import { ATTR_TYPES_NAMES } from "../utils";
import _isEqual from "lodash/isEqual";
import _cloneDeep from "lodash/cloneDeep";
import EditInitialAttributes from "./EditInitialAttributes.vue";
import AddNewAttributes from "./AddNewAttributes.vue";

import TextInput from "./inputs/TextInput.vue";
import Checkbox from "./inputs/Checkbox.vue";

export default {
  name: "SchemaEdit",
  components: { EditInitialAttributes, AddNewAttributes, TextInput, Checkbox },
  data() {
    return {
      schema: null,
      schemas: [],
      name: "",
      slug: "",
      reviewable: null,
      initialSchema: null,
      initialAttributeDefinitions: [],
      attributeDefinitions: [],
      attributes: [],
      ATTR_TYPES_NAMES,
    };
  },
  async created() {
    let resp = await api.getSchema({ slugOrId: this.$route.params.slugOrId });
    const schema = await resp.json();
    this.schema = schema;

    resp = await api.getAttributes();
    this.attributes = await resp.json();

    resp = await api.getSchemas();
    this.schemas = await resp.json();

    this.initialSchema = _cloneDeep(this.schema)
    this.initSchema(this.schema);
  },
  methods: {
    clone(obj) {
      return _cloneDeep(obj);
    },

    initSchema(schema) {
      this.name = schema.name;
      this.slug = schema.slug;
      this.reviewable = schema.reviewable;
      this.initialAttributeDefinitions = _cloneDeep(schema.attributes);
    },

    async sendData() {
      const initialData = this.$refs.initial.getData();
      const initialAttrs = initialData.attributes;
      const newAttrs = this.$refs.new.getData();
      
      let names = [];
      initialAttrs.map((x) => names.push(x.name));
      newAttrs.map((x) => names.push(x.name));
      if (new Set(names).size != names.length) {
        console.error("Got attributes with same names");
        return;
      }

      const add = newAttrs;
      const update = [];
      const remove = [...initialData.delete];

      for (const attr of initialAttrs) {
        if (attr.initialName && attr.initialName != attr.name) {
          update.push(attr);
        } else {
          delete attr.initialName;
          const initialAttr = this.schema.attributes.filter(
            (x) => x.name == attr.name
          )[0];
          if (!_isEqual(attr, initialAttr)) {
            update.push(attr);
          }
        }
      }
      for (const attr of newAttrs) {
        const sameAttr = initialData.delete.filter(
          (x) => x.name == attr.name && x.type == attr.type
        );
        if (sameAttr.length) {
          console.error("Added same attr as already was");
          return;
        }
      }

      const toSend = {
        name: this.name,
        slug: this.slug,
        reviewable: this.reviewable,
      };
      toSend.add_attributes = add;
      toSend.update_attributes = update.map((x) => {
        if (x.initialName) {
          return { ...x, name: x.initialName, new_name: x.name };
        }
        return x;
      });
      toSend.delete_attributes = remove.map((x) => x.name);

      const response = await api.updateSchema({
        schemaSlug: this.schema.slug,
        body: toSend,
      });
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