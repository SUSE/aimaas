<template>
  <div class="d-flex gap-3 flex-wrap">
    <div class="groups-list">
      <ul class="list-group">
        <GroupListItem
          v-for="group in rootGroups"
          :group="group"
          :groups="groups"
          :tree="tree"
          :key="group.id"
          @groupSelected="selectGroup"
        />
      </ul>
      <div class="d-flex mt-2">
        <ModalDialog
          :modal-buttons="addGroupModalButtons"
          :toggle-button="toggleButton"
          modal-title="Add new group"
        >
          <template v-slot:content>
            <GroupForm :show-save-button="false" ref="addGroupModalContent" />
          </template>
        </ModalDialog>
      </div>
    </div>
    <div v-show="activeGroup" class="group-detail">
      <div v-if="activeGroup" class="d-flex justify-content-between">
        <h4 class="">{{ activeGroup.name }}</h4>
        <ConfirmButton
          :callback="() => { deleteGroup(activeGroup.id); activeGroup = undefined }"
          btnClass="btn-outline-danger order-last"
          :reverse="true"
        >
          <template v-slot:label>
            <i class="eos-icons me-1">delete</i>
            Delete group
          </template>
        </ConfirmButton>
      </div>
      <Tabbing :tabs="tabs" :bind-args="bindArgs" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref, markRaw } from "vue";
import { Button, ModalButton } from "@/composables/modals";
import ConfirmButton from "@/components/inputs/ConfirmButton";
import GroupMembers from "@/components/auth/GroupMembers";
import GroupForm from "@/components/auth/GroupForm";
import GroupListItem from "@/components/auth/GroupListItem";
import Tabbing from "@/components/layout/Tabbing";
import ModalDialog from "@/components/layout/ModalDialog";
import PermissionList from "@/components/auth/PermissionList";
import { useAuthStore } from "../../store/auth";

const { groups, tree, loadGroupData, deleteGroup, createGroup } = useAuthStore();

const toggleButton = new Button({
  css: "btn-outline-primary flex-grow-1",
  icon: "group_add",
  text: "Add group",
});

const addGroupModalContent = ref(null);
const addGroupModalButtons = [
  new ModalButton({
    css: "btn-primary",
    icon: "group_add",
    text: "Add",
    callback: () => {
      createGroup(addGroupModalContent.value.myGroup)
    },
  }),
];

const tabs = [
  {
    name: "Members",
    component: markRaw(GroupMembers),
    icon: "groups",
    tooltip: "Manage group members",
  },
  {
    name: "Edit",
    component: markRaw(GroupForm),
    icon: "mode_edit",
    tooltip: "Change group details",
  },
  {
    name: "Permissions",
    component: markRaw(PermissionList),
    icon: "security",
    tooltip: "Manage group permissions",
  },
];

const bindArgs = computed(() => (
  [
    { group: activeGroup.value },
    { group: activeGroup.value },
    { recipientType: "Group", recipientId: activeGroup.value?.id },
  ]
));


const rootGroups = computed(() => {
  return tree.value[null]?.map((i) => groups.value[i]);
})

const activeGroup = ref();
function selectGroup(newGroup) {
  if (newGroup.id === activeGroup.value?.id) {
    activeGroup.value = undefined;
  } else {
    activeGroup.value = newGroup
  }
}

await loadGroupData();
</script>

<style lang="css" scoped>
.groups-list {
  flex: 1;
  min-width: 220px;
}

.group-detail {
  flex: 2;
  min-width: 360px;
}
</style>
