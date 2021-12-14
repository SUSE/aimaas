<template>
  <div v-if="details">
    <TextInput label="Name" v-model="details.name" :args="{ id: 'name' }"/>
    <TextInput label="Slug" v-model="details.slug" :args="{ id: 'slug' }">
      <template v-slot:helptext>
        URL-friendly ID of schema
      </template>
    </TextInput>
    <Checkbox
        label="Review"
        v-model="details.reviewable"
        :args="{ id: 'reviewable', class: 'mb-3' , tooltip: 'Require reviews for schema and entity changes?'}">
    </Checkbox>
    <h3 class="mt-3">Attributes</h3>
    <EditAttributes ref="initial" :schemas="availableSchemas"
                    :initialAttributes="clone(schema.attributes)"
                    :availableFieldNames="availableFieldNames"/>
    <button @click="sendData" type="button" class="mt-3 mb-3 btn btn-outline-primary">
      <i class='eos-icons'>save</i>
      Update schema
    </button>
  </div>
  <div v-else class="d-flex justify-content-center py-4">
    <div class="spinner-border" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
  </div>
</template>

<script>
import {api} from "@/api";
import {ATTR_TYPES_NAMES} from "@/utils";
import _isEqual from "lodash/isEqual";
import _cloneDeep from "lodash/cloneDeep";
import EditAttributes from "@/components/EditAttributes.vue";

import TextInput from "@/components/inputs/TextInput.vue";
import Checkbox from "@/components/inputs/Checkbox.vue";

export default {
  name: "SchemaEdit",
  components: {EditAttributes, TextInput, Checkbox},
  props: ["schema"],
  inject: ["availableSchemas"],
  data() {
    return {
      details: null,
      attributeDefinitions: [],
      attributes: [],
      ATTR_TYPES_NAMES,
    };
  },
  async created() {
    this.attributes = await api.getAttributes();
  },
  mounted() {
    if (this.details === null) {
      this.getDetails();
    }
  },
  methods: {
    clone(obj) {
      return _cloneDeep(obj);
    },
    getDetails() {
      api.getSchema({slugOrId: this.schema.slug}).then(details => {
        this.details = details;
        this.attributeDefinitions = _cloneDeep(details.attributes);
      });
    },
    async sendData() {
      const initialData = this.$refs.initial.getData();
      const initialAttrs = initialData.attributes;
      const newAttrs = initialData.additions

      let names = [];
      initialAttrs.map((x) => names.push(x.name));
      if (new Set(names).size !== names.length) {
        console.error("Got attributes with same names");
        return;
      }

      const add = [...initialData.additions];
      const update = [];
      const remove = [...initialData.deleted];

      for (const attr of initialAttrs) {
        if (attr.initialName && attr.initialName !== attr.name) {
          update.push(attr);
        } else {
          delete attr.initialName;
          const initialAttr = this.schema.attributes.filter(
              (x) => x.name === attr.name
          )[0];
          if (!_isEqual(attr, initialAttr)) {
            update.push(attr);
          }
        }
      }
      for (const attr of newAttrs) {
        const sameAttr = initialData.deleted.filter(
            (x) => x.name === attr.name && x.type === attr.type
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
          return {...x, name: x.initialName, new_name: x.name};
        }
        return x;
      });
      toSend.delete_attributes = remove.map((x) => x.name);

      const response = await api.updateSchema({
        schemaSlug: this.schema.slug,
        body: toSend,
      });
      if (response.status === 200) {
        this.$router.push({name: this.schema.slug});
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
  },
  watch: {
    schema() {
      this.getDetails();
    }
  },
};
</script>