<template>
  <template v-for="(attr, rowIndex) in attributes" :key="rowIndex">
    <input type="hidden" v-model="attributes[rowIndex].id">
    <TextInput label="Name" v-model="attributes[rowIndex].name"
               :args="{ id: `initialattrName${rowIndex}`, list: 'attributes' }"
               @change="onChange()"/>
    <SelectInput label="Type" v-model="attributes[rowIndex].type" @change="onChange()"
                 :args="{ id: `initialattrType${rowIndex}`, disabled: attr.id }"
                 :options="Object.keys(ATTR_TYPES_NAMES).map((type) => {
                   return { value: type, text: ATTR_TYPES_NAMES[type] };
                 })"/>
    <SelectInput v-if="attributes[rowIndex].type === 'FK'" label="Bind to schema"
                 @change="onChange()" v-model="attributes[rowIndex].bind_to_schema"
                 :options="schemasToBind.map((schema) => {
                   return { value: schema.id, text: schema.name };
                 })"
                 :args="{ id: `initialboundFK${rowIndex}`, disabled: attr.id }"/>
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
  props: ["schema", "schemas"],
  emits: ["change"],
  components: {TextInput, Checkbox, SelectInput, Textarea},
  data() {
    return {
      attributes: [],
      ATTR_TYPES_NAMES,
    };
  },
  async mounted() {
    await this.cloneAttrs();
  },
  methods: {
    onChange() {
      this.$emit("change");
    },
    cloneAttrs() {
      this.attributes = _cloneDeep(this.schema.attributes);
    },
    getData() {
      return {
        attributes: this.attributes
      };
    },
    removeAttr(index) {
      this.attributes.splice(index, 1);
    },
    addAttr() {
      let attr = {
        name: '', type: 'STR', key: false, unique: false, required: false, list: false,
        bind_to_schema: null, id: null
      };
      this.attributes.push(attr);
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