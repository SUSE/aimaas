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

<script setup>
import { ref, computed, watch } from "vue";
import _ from "lodash";
import TextInput from "@/components/inputs/TextInput.vue";
import DropdownSelect from "@/components/inputs/DropdownSelect.vue";
import { useAuthStore } from "@/store/auth";

const emit = defineEmits(["update"]);
const props = defineProps({
  group: {
    type: Object,
    required: false
  },
  showSaveButton: {
    type: Boolean,
    required: false,
    default: true
  }
});

const { groups, createGroup, updateGroup } = useAuthStore();

const myGroup = ref({name: '', parent_id: null, id: null});
if (props.group) {
  myGroup.value = _.cloneDeep(props.group);
}
defineExpose({ myGroup });

watch(() => props.group, () => {
  if(props.group.id !== myGroup.value.id) {
    myGroup.value = _.cloneDeep(props.group);
  }
})

const parentOptions = computed(() => {
  return Object.values(groups.value || {}).map(g => {return {text: g.name, value: g.id}});
});
  
async function onSave() {
  const groupData = {
    name: myGroup.value.name,
    parent_id: myGroup.value.parent_id
  }
  let response;
  if (myGroup.value?.id) {
    await updateGroup(myGroup.value.id, groupData);
  } else {
    await createGroup(groupData);
  }

  myGroup.value = {name: '', parent_id: null, id: null};
  emit("update", response);
}
</script>
