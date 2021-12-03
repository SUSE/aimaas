<template>
  <h3>Name</h3>
  <input v-model="this.name" type="text" class="form-control" />

  <h3>Slug</h3>
  <input v-model="this.slug" type="text" class="form-control" />
  <div v-for="attr in schema.attributes" :key="attr.name" class="col-6 mt-3">
    <h4>{{ this.titleCase(attr.name) }}</h4>
    <!-- ATTRIBUTE IS SINGLE VALUED -->
    <template v-if="!attr.list">
      <!-- ATTRIBUTE IS NOT OF REFERENCE TYPE -->
      <template v-if="attr.type != 'FK'">
        <component
          :is="TYPE_INPUT_MAP[attr.type]"
          v-model="this.singleValues[attr.name]"
        />
      </template>

      <template v-else>
        <!-- ATTRIBUTE IS REFERENCE -->
        <input
          :value="this.singleValues[attr.name]?.name"
          disabled
          class="form-control"
        />
        <ReferencedEntitySelect
          v-model="this.fkSearchInput[attr.name]"
          :foundEntities="fkSearchResults[attr.name]"
          :schemaSlug="fkSchemasSlugs[attr.name]"
          @changed="this.searchFK(attr.name)"
          @selected="this.singleValues[attr.name] = $event"
        />
      </template>
    </template>
    <!-- ATTRIBUTE IS LIST -->
    <template v-else>
      <!-- ATTRIBUTE IS NOT REFERENCE TYPE -->
      <template v-if="attr.type != 'FK'">
        <div
          v-for="(val, index) in listValues[attr.name]"
          :key="index"
          class="row mb-3"
        >
          <div class="col">
            <component
              :is="TYPE_INPUT_MAP[attr.type]"
              v-model="listValues[attr.name][index]"
            />
          </div>
          <div class="col mt-1">
            <button
              @click="this.listValues[attr.name].splice(index, 1)"
              type="button"
              class="btn btn-sm btn-outline-secondary"
            >
              Remove
            </button>
          </div>
        </div>

        <button
          @click="this.listValues[attr.name].push(null)"
          class="my-3 btn btn-sm btn-primary"
          type="button"
        >
          Add value
        </button>
      </template>

      <!-- ATTRIBUTE IS REFERENCE -->
      <template v-else>
        <form class="row row-cols-lg-auto g-3 align-items-center">
          <div class="col">
            <ReferencedEntityListSelect
              v-model="this.fkSearchInput[attr.name]"
              :foundEntities="fkSearchResults[attr.name]"
              :schemaSlug="fkSchemasSlugs[attr.name]"
              :selectedEntities="this.listValues[attr.name]"
              @changed="this.searchFK(attr.name)"
              @select="addListValue(attr.name, $event)"
              @unselect="removeListValue(attr.name, $event)"
            />
          </div>
        </form>
      </template>
    </template>
  </div>
  <button
    @click="$emit('submit', this.assembleBody())"
    type="button"
    class="my-3 btn btn-primary"
  >
    Save changes
  </button>
</template>

<script>
import IntegerInput from "./inputs/IntegerInput.vue";
import FloatInput from "./inputs/FloatInput.vue";
import TextInput from "./inputs/TextInput.vue";
import Checkbox from "./inputs/Checkbox.vue";
import DateTime from "./inputs/DateTime.vue";
import DateInput from "./inputs/DateInput.vue";
import ReferencedEntitySelect from "./inputs/ReferencedEntitySelect.vue";
import ReferencedEntityListSelect from "./inputs/ReferencedEntityListSelect.vue";
import { api } from "../api";

const TYPE_INPUT_MAP = {
  STR: "TextInput",
  DT: "DateTime",
  INT: "IntegerInput",
  FLOAT: "FloatInput",
  BOOL: "Checkbox",
  DATE: "DateInput",
};

export default {
  name: "EntityCreateEditForm",
  emits: ["submit"],
  props: ["schema", "entity"],
  components: {
    TextInput,
    Checkbox,
    DateTime,
    DateInput,
    IntegerInput,
    FloatInput,
    ReferencedEntitySelect,
    ReferencedEntityListSelect,
  },
  async created() {
    await this.initValues(this.schema);
  },
  computed: {},
  data() {
    return {
      name: "",
      slug: "",
      singleValues: {},
      listValues: {},
      fkSchemasSlugs: {},
      fkSearchResults: {},
      fkSearchInput: {},
      TYPE_INPUT_MAP,
      singleInitHandlers: {
        FK: async (attr) => {
          return await (
            await api.getEntity({
              schemaSlug: this.fkSchemasSlugs[attr.name],
              entityIdOrSlug: this.entity[attr.name],
            })
          ).json();
        },
        DT: async (attr) => {
          return this.entity[attr.name]
            ? new Date(this.entity[attr.name])
                .toISOString()
                .substring(
                  0,
                  new Date(this.entity[attr.name]).toISOString().length - 2
                )
            : null;
        },
      },
    };
  },
  methods: {
    async initAttrValue(attr) {
      if (attr.type == "FK") {
        this.fkSearchResults[attr.name] = [];
        this.fkSearchInput[attr.name] = "";
        const schema = await (
          await api.getSchema({ slugOrId: attr.bind_to_schema })
        ).json();
        this.fkSchemasSlugs[attr.name] = schema.slug;
      }
      if (attr.list) {
        await this.initMultiValueAttr(attr);
      } else {
        await this.initSingleValueAttr(attr);
      }
    },

    async initSingleValueAttr(attr) {
      if (this.entity) {
        const handler = this.singleInitHandlers[attr.type];
        if (!handler) {
          this.singleValues[attr.name] = this.entity[attr.name];
        } else {
          this.singleValues[attr.name] = await handler(attr);
        }
      } else {
        this.singleValues[attr.name] = null;
      }
    },

    async initMultiValueAttr(attr) {
      if (this.entity) {
        if (attr.type == "FK")
          this.listValues[attr.name] = await Promise.all(
            this.entity[attr.name].map(
              async (id) =>
                await (
                  await api.getEntity({
                    schemaSlug: this.fkSchemasSlugs[attr.name],
                    entityIdOrSlug: id,
                  })
                ).json()
            )
          );
        else {
          this.listValues[attr.name] = [...this.entity[attr.name]]; // TODO this one doesnt handle different types like DT
        }
      } else {
        this.listValues[attr.name] = [];
      }
    },
    initValues(schema) {
      if (this.entity) {
        this.name = this.entity.name;
        this.slug = this.entity.slug;
      }

      schema.attributes.map(async (attr) => {
        await this.initAttrValue(attr);
      });
    },
    addListValue(attrName, value) {
      this.listValues[attrName].push(value);
    },
    removeListValue(attrName, index) {
      this.listValues[attrName].splice(index, 1);
    },
    titleCase(str) {
      var splitStr = str.toLowerCase().split("_");
      for (var i = 0; i < splitStr.length; i++) {
        splitStr[i] =
          splitStr[i].charAt(0).toUpperCase() + splitStr[i].substring(1);
      }
      return splitStr.join(" ");
    },
    isFKinList(attrName, slug) {
      return !this.listValues[attrName].some((x) => x.slug == slug);
    },
    async searchFK(attrName) {
      const query = this.fkSearchInput[attrName];
      const fkSchema = this.fkSchemasSlugs[attrName];
      const resp = await api.getEntities({
        schemaSlug: fkSchema,
        limit: 5,
        filters: {
          "name.contains": query,
        },
      });
      const json = await resp.json();
      this.fkSearchResults[attrName] = json.entities;
    },
    getAttrType(attr) {
      return this.schema.attributes.filter((x) => x.name == attr)[0].type;
    },
    assembleBody() {
      const body = { name: this.name, slug: this.slug };
      for (const [attr, value] of Object.entries(this.singleValues)) {
        if (this.getAttrType(attr) == "FK") {
          body[attr] = value?.id;
        } else {
          body[attr] = value;
        }
      }
      for (const [attr, valueList] of Object.entries(this.listValues)) {
        if (this.getAttrType(attr) == "FK") {
          body[attr] = valueList.map((x) => x.id);
        } else {
          body[attr] = valueList;
        }
      }
      return body;
    },
  },
};
</script>