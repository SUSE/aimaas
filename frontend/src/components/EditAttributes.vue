<template>
  <template v-for="(attr, rowIndex) in attributes" :key="rowIndex">
    <TextInput label="Name" v-model="attributes[rowIndex].name"
               :args="{ id: `initialattrName${rowIndex}`, list: 'attributes' }">
      <template v-slot:datalist>
        <option v-for="(attr, index) in availableFieldNames" :key="index" :value="attr.name">
          {{ `${attr.name} (${attr.type})` }}
        </option>
      </template>
    </TextInput>
    <Select label="Type" v-model="attributes[rowIndex].type"
            :args="{ id: `initialattrType${rowIndex}`, disabled: !attr.isNew }"
            :options="
              Object.keys(ATTR_TYPES_NAMES).map((type) => {
                return { value: type, text: ATTR_TYPES_NAMES[type] };
              })"/>
    <Select v-if="attributes[rowIndex].type === 'FK'" label="Bind to schema"
            v-model="attributes[rowIndex].bind_to_schema"
            :options="schemasToBind.map((schema) => {
                return { value: schema.id, text: schema.name };
              })"
            :args="{ id: `initialboundFK${rowIndex}`, disabled: !attr.isNew }"/>
    <Textarea label="Description"
              v-model="attributes[rowIndex].description"
              :args="{ id: `initialDescription${rowIndex}` }">
      <template v-slot:helptext>
        (optional)
      </template>
    </Textarea>
    <div class="row mb-2 border-bottom">
      <div class="col-lg-2 d-grid px-3 py-1">
        <button @click="removeAttr(rowIndex)" type="button" class="btn btn-outline-danger"
                data-bs-toggle="tooltip" title="Delete attribute from schema">
          <i class='eos-icons me-1'>delete</i>
          Remove
        </button>
      </div>
      <div class="col-lg-10">
        <div class="container">
          <div class="row g-2">
            <div class="col-md-3">
              <Checkbox label="Key" v-model="attributes[rowIndex].key" without-offset="true"
                        :args="{ id: `initialkey${rowIndex}`, tooltip: 'Include attribute in entity listing?' }"/>
            </div>
            <div class="col-md-3">
              <Checkbox label="Unique" v-model="attributes[rowIndex].unique" without-offset="true"
                        :args="{ id: `initialunique${rowIndex}`, tooltip: 'Must value be unique for all entities in schema?' }"/>
            </div>
            <div class="col-md-3">
              <Checkbox label="Required" v-model="attributes[rowIndex].required"
                        without-offset="true"
                        :args="{ id: `initialrequired${rowIndex}`, tooltip: 'Must value be specified?' }"/>
            </div>
            <div class="col-md-3">
              <Checkbox label="List" v-model="attributes[rowIndex].list" without-offset="true"
                        :args="{ id: `initiallist${rowIndex}`, tooltip: 'May attribute store multiple values?' }"/>
            </div>
          </div>
        </div>
      </div>
    </div>
  </template>
  <button @click="addAttr()" type="button" class="btn btn-outline-secondary"
          data-bs-toggle="tooltip" title="Add new attribute to schema">
    <i class='eos-icons me-1'>add_circle</i>
    New attribute
  </button>
</template>

<script>
import {ref} from "vue";
import _cloneDeep from "lodash/cloneDeep";
import TextInput from "@/components/inputs/TextInput.vue";
import Textarea from "@/components/inputs/Textarea.vue";
import Checkbox from "@/components/inputs/Checkbox.vue";
import Select from "@/components/inputs/Select.vue";
import {ATTR_TYPES_NAMES} from "@/utils";

export default {
  name: "EditAttributes",
  props: ["schema", "schemas", "availableFieldNames"],
  components: {TextInput, Checkbox, Select, Textarea},
  data() {
    return {
      attributes: [],
      attrsToDelete: [],
      attrsToAdd: [],
      initialAttrNames: [],
      ATTR_TYPES_NAMES,
    };
  },
  async mounted() {
    await this.cloneAttrs();
  },
  methods: {
    cloneAttrs() {
      this.attributes = _cloneDeep(this.schema.attributes);
      this.attributes.map((x) => (x.initialName = x.name));
    },
    getData() {
      return {
        attributes: this.attributes,
        deleted: this.attrsToDelete,
        additions: this.attrsToAdd
      };
    },
    removeAttr(index) {
      const attr = this.attributes[index];
      this.attributes.splice(index, 1);
      this.attrsToDelete.push(attr);
    },
    addAttr() {
      let attr = {
        name: '', type: null, key: false, unique: false, required: false, list: false,
        bind_to_schema: null, isNew: true
      };
      this.attributes.push(attr);
      this.attrsToAdd.push(ref(attr));
    }
  },
  computed: {
    schemasToBind() {
      return [{id: -1, name: "<this/new schema>"}, ...this.schemas];
    },
  },
  watch: {
    schema() {
      this.cloneAttrs();
    }
  }
};
</script>