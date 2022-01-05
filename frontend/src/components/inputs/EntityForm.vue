<template>
  <Spinner :loading="loading">
    <div v-if="!loading" class="container">
      <TextInput label="Name" v-model="entity.name" :args="{ id: 'name', maxlength: 128 }"
                 :required="true"/>
      <TextInput label="Slug" v-model="entity.slug" :args="{ id: 'slug', maxlength: 128 }"
                 :required="true"/>

      <h3 class="mt-3">Attributes</h3>
      <template v-for="attr in schemaDetails.attributes" :key="attr.name">
        <!-- ATTRIBUTE IS REFERENCE -->
        <template v-if="attr.type === 'FK'">
          <ReferencedEntitySelect v-model="entity[attr.name]" :label="attr.name"
                                  :args="{id: attr.name}" :fk-schema-id="attr.bind_to_schema"
                                  :select-type="attr.list ? 'many': 'single'"
                                  :required="requiredAttrs.includes(attr.name)"/>
        </template>
        <!-- ATTRIBUTE IS SINGLE VALUED -->
        <template v-else-if="!attr.list">
          <component :is="TYPE_INPUT_MAP[attr.type]" v-model="entity[attr.name]"
                     :label="attr.name" :args="{id: attr.name}"
                     :required="requiredAttrs.includes(attr.name)"/>
        </template>
        <!-- ATTRIBUTE IS MULTI VALUED -->
        <template v-else>
          <div class="row mb-1 pb-1 border-bottom border-light">
            <div class="col-lg-2">
              {{ attr.name }}
            </div>
            <div class="col-lg-10">
              <ul class="list-group">
                <li v-for="(val, idx) in (entity[attr.name] || [])" :key="`${attr.name}-${idx}`"
                    class="list-group-item d-flex">
                  <div class="flex-grow-1">
                    <component :is="TYPE_INPUT_MAP[attr.type]" v-model="entity[attr.name][idx]"
                               :vertical="true" :args="{id: `${attr.name}-${idx}`}"
                               :required="requiredAttrs.includes(attr.name)"/>
                  </div>
                  <div>
                    <button type="button" class="btn btn-outline-cta ms-1"
                            data-ts-toggle="tooltip" title="Remove">
                      <i class="eos-icons">backspace</i>

                    </button>
                  </div>
                </li>
              </ul>
              <div class="d-grid gap-2">
                <button type="button" class="btn btn-outline-primary float-end mt-1"
                        data-ts-toggle="tooltip" title="Add value" @click="addListItem(attr.name)">
                  <i class="eos-icons">add</i>
                  Add
                </button>
              </div>
            </div>
          </div>
        </template>
      </template>
      <div class="d-grid gap-2 mt-1">
        <button type="button" class="btn btn-primary p-2" @click="sendBody">
          <i class="eos-icons me-1">save</i>
          Save changes
        </button>
      </div>
    </div>
  </Spinner>
</template>

<script>
import _cloneDeep from "lodash/cloneDeep";
import _isEqual from "lodash/isEqual";

import TextInput from "@/components/inputs/TextInput";
import Checkbox from "@/components/inputs/Checkbox";
import DateTime from "@/components/inputs/DateTime";
import DateInput from "@/components/inputs/DateInput";
import IntegerInput from "@/components/inputs/IntegerInput";
import FloatInput from "@/components/inputs/FloatInput";
import ReferencedEntitySelect from "@/components/inputs/ReferencedEntitySelect";
import Spinner from "@/components/layout/Spinner";
import {TYPE_INPUT_MAP} from "@/utils";


export default {
  name: "EntityForm",
  components: {
    Spinner, TextInput, Checkbox, DateTime, DateInput, IntegerInput, FloatInput,
    ReferencedEntitySelect
  },
  props: ["schema"],
  inject: ["activeSchema", "updatePendingRequests"],
  emits: ["update"],
  created() {
    this.updateSchemaMeta();
  },
  watch: {
    activeSchema() {
      this.updateSchemaMeta();
    }
  },
  data() {
    return {
      entity: null,
      origEntity: null,
      schemaDetails: null,
      loading: true,
      TYPE_INPUT_MAP
    };
  },
  computed: {
    requiredAttrs() {
      return (this.schemaDetails?.attributes || []).filter(a => a.required).map(a => a.name);
    }
  },
  methods: {
    addListItem(attrName) {
      if (this.entity[attrName] instanceof Array) {
        this.entity[attrName].push('');
      } else {
        console.error("Attribute", attrName, "is not a multi-value attribute!");
      }
    },
    prepEntity() {
      const listAttrs = this.schemaDetails.attributes.filter(x => x.list);
      if (this.entity === null) {
        this.entity = {name: null, slug: null};
        for (const attr of this.schemaDetails.attributes) {
          this.entity[attr.name] = null;
        }
      }
      for (const attr of listAttrs) {
        if (this.entity && !this.entity[attr.name]) {
          this.entity[attr.name] = [];
        }
      }
      this.origEntity = _cloneDeep(this.entity);
      this.$emit("update", this.entity);
    },
    updateSchemaMeta() {
      const promises = [];
      let p;
      this.loading = true;

      p = this.$api.getSchema({slugOrId: this.$route.params.schemaSlug}).then(
          details => this.schemaDetails = details
      );
      promises.push(p);
      if (this.$route.params.entitySlug) {
        p = this.$api.getEntity({
          schemaSlug: this.$route.params.schemaSlug,
          entityIdOrSlug: this.$route.params.entitySlug,
        }).then(data => {
          this.entity = data;
        });
        promises.push(p);
      }

      Promise.all(promises).then(() => {
        this.prepEntity();
        this.loading = false;
      });
    },
    getChanges() {
      const result = {};
      for (const [attr, value] of Object.entries(this.entity)) {
        if (!_isEqual(value, this.origEntity[attr])) {
          result[attr] = value;
        }
      }
      return result;
    },

    async sendBody() {
      this.loading = true;
      let response;
      if (this.$route.params.entitySlug) {
        // UPDATE EXISTING ENTITY
        const body = this.getChanges();
        if (Object.keys(body).length === 0) {
          console.info("No changes, therefore pushing nothing to server.");
          this.loading = false;
          return;
        }
        response = await this.$api.updateEntity({
          schemaSlug: this.$route.params.schemaSlug,
          entityIdOrSlug: this.$route.params.entitySlug,
          body: body,
        });
        this.loading = false;
      } else {
        // CREATE NEW ENTITY
        response = await this.$api.createEntity({
          schemaSlug: this.$route.params.schemaSlug,
          body: this.entity
        });
        this.loading = false;
      }
      if (response) {
        this.updatePendingRequests();
      }
    },
  },
}
</script>

<style scoped>

</style>