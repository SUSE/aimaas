<template>
  <template v-for="(attr, rowIndex) in attributes" :key="rowIndex">
    <TextInput label="Name" v-model="attributes[rowIndex].name"
               :args="{ id: `initialattrName${rowIndex}`, list: 'attributes' }"
               @change="onChange()">
      <template v-slot:datalist>
        <option v-for="(attr, index) in availableFieldNames" :key="index" :value="attr.name">
          {{ `${attr.name} (${attr.type})` }}
        </option>
      </template>
    </TextInput>
    <SelectInput label="Type" v-model="attributes[rowIndex].type" @change="onChange()"
                 :args="{ id: `initialattrType${rowIndex}`, disabled: !attr.isNew }"
                 :options="Object.keys(ATTR_TYPES_NAMES).map((type) => {
                   return { value: type, text: ATTR_TYPES_NAMES[type] };
                 })"/>
    <SelectInput v-if="attributes[rowIndex].type === 'FK'" label="Bind to schema"
                 @change="onChange()" v-model="attributes[rowIndex].bind_to_schema"
                 :options="schemasToBind.map((schema) => {
                   return { value: schema.id, text: schema.name };
                 })"
                 :args="{ id: `initialboundFK${rowIndex}`, disabled: !attr.isNew }"/>
    <Textarea label="Description" @change="onChange()"
              v-model="attributes[rowIndex].description"
              :args="{ id: `initialDescription${rowIndex}` }">
      <template v-slot:helptext>
        (optional)
      </template>
    </Textarea>
    <div class="row mb-2 border-bottom">
      <div class="col-lg-2 d-grid px-3 py-1">
        <button @click="removeAttr(rowIndex); onChange()" type="button" class="btn btn-outline-danger"
                data-bs-toggle="tooltip" title="Delete attribute from schema">
          <i class='eos-icons me-1'>delete</i>
          Remove
        </button>
      </div>
      <div class="col-lg-10">
        <div class="container">
          <div class="row g-2">
            <div class="col-md-3">
              <Checkbox label="Key" v-model="attributes[rowIndex].key" :without-offset="true"
                        @change="onChange()"
                        :args="{ id: `initialkey${rowIndex}`, tooltip: 'Include attribute in entity listing?' }"/>
            </div>
            <div class="col-md-3">
              <Checkbox label="Unique" v-model="attributes[rowIndex].unique" :without-offset="true"
                        @change="onChange()"
                        :args="{ id: `initialunique${rowIndex}`, tooltip: 'Must value be unique for all entities in schema?' }"/>
            </div>
            <div class="col-md-3">
              <Checkbox label="Required" v-model="attributes[rowIndex].required"
                        :without-offset="true" @change="onChange()"
                        :args="{ id: `initialrequired${rowIndex}`, tooltip: 'Must value be specified?' }"/>
            </div>
            <div class="col-md-3">
              <Checkbox label="List" v-model="attributes[rowIndex].list" :without-offset="true"
                        @change="onChange()"
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
import _cloneDeep from "lodash/cloneDeep";
import TextInput from "@/components/inputs/TextInput.vue";
import Textarea from "@/components/inputs/Textarea.vue";
import Checkbox from "@/components/inputs/Checkbox.vue";
import SelectInput from "@/components/inputs/SelectInput.vue";
import {ATTR_TYPES_NAMES} from "@/utils";

export default {
  name: "EditAttributes",
  props: ["schema", "schemas", "availableFieldNames"],
  emits: ["change"],
  components: {TextInput, Checkbox, SelectInput, Textarea},
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
    onChange() {
      console.debug("Hello, something changed!")
      this.$emit("change");
    },
    cloneAttrs() {
      this.attributes = _cloneDeep(this.schema.attributes);
      this.attributes.map((x) => (x.initialName = x.name));
    },
    _remove_isNew(attr) {
      if (attr.isNew) {
            delete attr.isNew;
          }
          return attr;
    },
    getData() {
      return {
        attributes: this.attributes.map(this._remove_isNew),
        deleted: this.attrsToDelete.map(this._remove_isNew),
        additions: this.attrsToAdd.map(this._remove_isNew)
      };
    },
    removeAttr(index) {
      const attr = this.attributes[index];
      this.attributes.splice(index, 1);

      const addIndex = this.attrsToAdd.indexOf(attr);
      if (addIndex > -1) {
        this.attrsToAdd.splice(addIndex, 1);
      } else {
        this.attrsToDelete.push(attr);
      }
    },
    addAttr() {
      let attr = {
        name: '', type: 'STR', key: false, unique: false, required: false, list: false,
        bind_to_schema: null, isNew: true
      };
      this.attributes.push(attr);
      this.attrsToAdd.push(attr);
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