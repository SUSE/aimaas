<template>
  <TextInput label="Name" :required="true" v-model="myGroup.name" :args="{id: 'name'}"/>
  <DropdownSelect label="Parent" :required="false" v-model="myGroup.parent_id"
                :args="{id: 'parent_id'}" :options="parentOptions"/>
  <div class="d-grid gap-2 mt-1" v-if="showSaveButton">
    <button type="button" class="btn btn-primary p-2" @click="onSave">
      <i class="eos-icons me-1">save</i>
      Save changes
    </button>
  </div>
</template>

<script>
import TextInput from "@/components/inputs/TextInput";
import DropdownSelect from "@/components/inputs/DropdownSelect";

export default {
  name: "GroupEdit",
  emits: ["update"],
  inject: ["groups"],
  components: {TextInput, DropdownSelect},
  props: {
    group: {
      type: Object,
      required: false
    },
    showSaveButton: {
      type: Boolean,
      required: false,
      default: true
    }
  },
  data() {
    return {
      myGroup: {name: '', parent_id: null, id: null}
    }
  },
  activated() {
    if (this.group) {
      this.myGroup = this.group;
    }
  },
  watch: {
    group() {
      this.myGroup = this.group;
    }
  },
  computed: {
    icon() {
      return this.myGroup?.id ? 'save': 'save';
    },
    text() {
      return this.myGroup?.id ? 'Save changes': 'Add';
    },
    parentOptions() {
      return Object.values(this.groups || {}).map(g => {return {text: g.name, value: g.id}});
    }
  },
  methods: {
    async onSave() {
      const body = {
        name: this.myGroup.name,
        parent_id: this.myGroup.parent_id
      }
      let response;
      if (this.myGroup?.id) {
        response = await this.$api.updateGroup({groupId: this.myGroup.id, body: body});
      } else {
        response = await this.$api.createGroup({body: body});
      }
      this.$emit("update", response);
    }
  }
}
</script>

<style scoped>

</style>