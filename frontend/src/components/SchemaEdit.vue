<template>
  <div v-if="details">
    <TextInput label="Name" v-model="details.name" :args="{ id: 'name', maxlength: 128 }"
               @change="hasChanged = true"/>
    <TextInput label="Slug" v-model="details.slug" :args="{ id: 'slug', maxlength: 128 }"
               @change="hasChanged = true">
      <template v-slot:helptext>
        URL-friendly ID of schema
      </template>
    </TextInput>
    <Checkbox
        label="Review"
        v-model="details.reviewable" @change="hasChanged = true"
        :args="{ id: 'reviewable', class: 'mb-3' , tooltip: 'Require reviews for schema and entity changes?'}">
    </Checkbox>
    <h3 class="mt-3">Attributes</h3>
    <EditAttributes ref="initial" :schemas="availableSchemas" :schema="details"
                    :availableFieldNames="availableFieldNames" @change="hasChanged = true"/>
    <div class="d-grid gap-2">
      <button @click="sendData" type="button" class="mt-3 mb-3 btn"
              :class="hasChanged? 'btn-primary' : 'btn-light'"
              :disabled="!hasChanged">
        <i class='eos-icons me-1'>save</i>
        <template v-if="schema">
          Update schema
        </template>
        <template v-else>
          Create schema
        </template>
      </button>
    </div>
  </div>
  <div v-else class="d-flex justify-content-center py-4">
    <div class="spinner-border" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
  </div>
</template>

<script>
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
      hasChanged: false
    };
  },
  async created() {
    this.attributes = await this.$api.getAttributes();
  },
  mounted() {
    if (this.details === null) {
      this.getDetails();
    }
  },
  methods: {
    getDetails() {
      if (this.schema) {
        this.$api.getSchema({slugOrId: this.schema.slug}).then(details => {
          this.details = details;
          this.attributeDefinitions = _cloneDeep(details.attributes);
        });
      } else {
        this.details = {name: "", slug: "", attributes: []};
      }
    },
    async sendData() {
      if (this.schema) {
        await this.updateSchema();
      } else {
        await this.createSchema();
      }
    },
    async createSchema() {
      const initialData = this.$refs.initial.getData();
      const json = {
        name: this.details.name,
        slug: this.details.slug,
        reviewable: this.details.reviewable,
        attributes: initialData.attributes,
      };
      const response = await this.$api.createSchema({ body: json });
      if (response !== undefined && response !== null) {
        this.$router.push({name: 'schema-view', params: {schemaSlug: json.slug}});
      }
    },
    async updateSchema() {
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
        if (initialData.additions.indexOf(attr) > -1 || initialData.deleted.indexOf(attr) > -1) {
          continue;
        }
        if (attr.initialName && attr.initialName !== attr.name) {
          update.push(attr);
        } else {
          delete attr.initialName;
          const initialAttr = this.details.attributes.filter(
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

      const response = await this.$api.updateSchema({
        schemaSlug: this.schema.slug,
        body: toSend,
      });
      if (response.status === 200) {
        this.$router.push({name: 'schema-view', params: {schemaSlug: this.schema.slug}});
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