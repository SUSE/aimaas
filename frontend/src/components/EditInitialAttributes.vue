<template>
  <template v-for="(attr, rowIndex) in attributes" :key="rowIndex">
    <form>
      <div class="row">
        <div class="col-lg-3">
          <TextInput
            label="Attribute name"
            v-model="attributes[rowIndex].name"
            :args="{ id: `initialattrName${rowIndex}`, list: 'attributes' }"
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
            v-model="attributes[rowIndex].type"
            :args="{ id: `initialattrType${rowIndex}`, disabled: true }"
            :options="
              Object.keys(ATTR_TYPES_NAMES).map((type) => {
                return { value: type, text: ATTR_TYPES_NAMES[type] };
              })
            "
          />
        </div>

        <div v-if="attributes[rowIndex].type == 'FK'" class="col">
          <Select
            label="Bind to schema"
            v-model="attributes[rowIndex].bind_to_schema"
            :options="
              schemasToBind.map((schema) => {
                return { value: schema.id, text: schema.name };
              })
            "
            :args="{ id: `initialboundFK${rowIndex}`, disabled: true }"
          />
        </div>

        <div class="col-lg-3">
          <Textarea
            label="Description (optional)"
            v-model="attributes[rowIndex].description"
            :args="{ id: `initialDescription${rowIndex}` }"
          />
        </div>
      </div>

      <div class="row">
        <div class="form">
          <div class="form-check form-check-inline">
            <Checkbox
              label="Key"
              v-model="attributes[rowIndex].key"
              :args="{ id: `initialkey${rowIndex}` }"
            />
          </div>
          <div class="form-check form-check-inline">
            <Checkbox
              label="Unique"
              v-model="attributes[rowIndex].unique"
              :args="{ id: `initialunique${rowIndex}` }"
            />
          </div>
          <div class="form-check form-check-inline">
            <Checkbox
              label="Required"
              v-model="attributes[rowIndex].required"
              :args="{ id: `initialrequired${rowIndex}` }"
            />
          </div>
          <div class="form-check form-check-inline">
            <Checkbox
              label="List"
              v-model="attributes[rowIndex].list"
              :args="{ id: `initiallist${rowIndex}` }"
            />
          </div>
        </div>
      </div>

      <div class="col">
        <button
          @click="removeAttr(rowIndex)"
          type="button"
          class="btn btn-sm btn-outline-danger"
        >
          Remove
        </button>
      </div>
    </form>
  </template>
</template>

<script>
import TextInput from "./inputs/TextInput.vue";
import Textarea from "./inputs/Textarea.vue";
import Checkbox from "./inputs/Checkbox.vue";
import Select from "./inputs/Select.vue";
import { ATTR_TYPES_NAMES } from "../utils";

export default {
  name: "EditInitialAttributes",
  props: ["initialAttributes", "schemas", "availableFieldNames"],
  components: { TextInput, Checkbox, Select, Textarea },
  data() {
    return {
      attributes: [],
      attrsToDelete: [],
      initialAttrNames: [],
      ATTR_TYPES_NAMES,
    };
  },
  async mounted() {
    this.attributes = this.initialAttributes;
    this.attributes.map((x) => (x.initialName = x.name));
  },
  methods: {
    getData() {
      return { attributes: this.attributes, delete: this.attrsToDelete };
    },
    removeAttr(index) {
      const attr = this.attributes[index];
      this.attributes.splice(index, 1);
      this.attrsToDelete.push(attr);
    },
  },
  computed: {
    schemasToBind() {
      return [{ id: -1, name: "<this new schema>" }, ...this.schemas];
    },
  },
};
</script>