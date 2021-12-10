<template>
  <template v-for="(attr, rowIndex) in attributeDefinitions" :key="rowIndex">
    <form>
      <div class="row">
        <div class="col-lg-3">
          <TextInput
            label="Attribute name"
            v-model="attributeDefinitions[rowIndex].name"
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
            v-model="attributeDefinitions[rowIndex].type"
            :options="
              Object.keys(ATTR_TYPES_NAMES).map((type) => {
                return { value: type, text: ATTR_TYPES_NAMES[type] };
              })
            "
            :args="{ id: `attrType${rowIndex}` }"
          />
        </div>

        <div
          v-if="attributeDefinitions[rowIndex].type == 'FK'"
          class="col"
        >
          <Select
            label="Bind to schema"
            v-model="attributeDefinitions[rowIndex].bind_to_schema"
            :options="
              schemasToBind.map((schema) => {
                return { value: schema.id, text: schema.name };
              })
            "
            :args="{ id: `boundFK${rowIndex}` }"
          />
        </div>

        <div class="col-lg-3">
          <Textarea
            label="Description (optional)"
            v-model="attributeDefinitions[rowIndex].description"
            :args="{ id: `description${rowIndex}` }"
          />
        </div>
      </div>
      <div class="row">
        <div class="form">
          <div class="form-check form-check-inline">
            <Checkbox
              label="Key"
              v-model="attributeDefinitions[rowIndex].key"
              :args="{ id: `key${rowIndex}` }"
            />
          </div>
          <div class="form-check form-check-inline">
            <Checkbox
              label="Unique"
              v-model="attributeDefinitions[rowIndex].unique"
              :args="{ id: `unique${rowIndex}` }"
            />
          </div>
          <div class="form-check form-check-inline">
            <Checkbox
              label="Required"
              v-model="attributeDefinitions[rowIndex].required"
              :args="{ id: `required${rowIndex}` }"
            />
          </div>
          <div class="form-check form-check-inline">
            <Checkbox
              label="List"
              v-model="attributeDefinitions[rowIndex].list"
              :args="{ id: `list${rowIndex}` }"
            />
          </div>
        </div>
      </div>
      <div class="col">
        <button
          @click="attributeDefinitions.splice(rowIndex, 1)"
          type="button"
          class="btn btn-sm btn-outline-danger"
        >
          Remove
        </button>
      </div>
    </form>
  </template>
  <form class="mt-3">
    <button
      @click="
        attributeDefinitions.push({
          name: '',
          type: null,
          key: false,
          unique: false,
          required: false,
          list: false,
          bind_to_schema: null,
        })
      "
      type="button"
      class="btn btn-sm btn-primary"
    >
      Add attribute
    </button>
  </form>
</template>

<script>
import TextInput from "./inputs/TextInput.vue";
import Textarea from "./inputs/Textarea.vue";
import Checkbox from "./inputs/Checkbox.vue";
import Select from "./inputs/Select.vue";
import { ATTR_TYPES_NAMES } from "../utils";

export default {
  name: "AddNewAttributes",
  components: { TextInput, Checkbox, Select, Textarea },
  props: ["schemas", "availableFieldNames"],
  methods: {
    getData() {
      return this.attributeDefinitions;
    },
  },
  computed: {
    schemasToBind() {
      return [{ id: -1, name: "<this new schema>" }, ...this.schemas];
    },
  },
  data() {
    return {
      attributeDefinitions: [],
      ATTR_TYPES_NAMES,
    };
  },
};
</script>