<template>
  <div class="row m-0">
    <div class="col-md-3">
      <ul class="list-group">
        <GroupListItem :group="group" v-for="group in rootGroups()" :key="group.id"
                       @groupSelected="switchGroup"/>
      </ul>
      <div class="d-flex mt-2">
        <ModalDialog :modal-buttons="modalButtons" :toggle-button="toggleButton"
                   modal-title="Add new group">
        <template v-slot:content>
          <GroupEdit :show-save-button="false" ref="groupAdd"/>
        </template>
      </ModalDialog>
        </div>
    </div>
    <div class="col-md-9">
      <h4 class="ps-5">{{ activeGroup?.name }}</h4>
      <Tabbing :tabs="tabs" :bind-args="bindArgs" v-show="activeGroup" ref="groupTab"/>
    </div>
  </div>
</template>

<script>
import {Button, ModalButton} from "@/composables/modals";
import GroupMembers from "@/components/auth/GroupMembers";
import GroupEdit from "@/components/auth/GroupEdit";
import GroupListItem from "@/components/auth/GroupListItem";
import Tabbing from "@/components/layout/Tabbing";
import ModalDialog from "@/components/layout/ModalDialog";
import PermissionList from "@/components/auth/PermissionList";

export default {
  name: "GroupManager",
  components: {ModalDialog, Tabbing, GroupListItem, GroupEdit},
  inject: ["groups", "tree"],
  data() {
    return {
      activeGroup: null,
      toggleButton: new Button({
        css: "btn-outline-primary flex-grow-1",
        icon: "group_add",
        text: "Add group"
      }),
      modalButtons: [
        new ModalButton({
          css: "btn-primary",
          icon: "group_add",
          text: "Add",
          callback: this.addGroup
        })
      ],
      tabs: [
        {
          name: "Members",
          component: GroupMembers,
          icon: "groups",
          tooltip: "Manage group members"
        },
        {
          name: "Edit",
          component: GroupEdit,
          icon: "mode_edit",
          tooltip: "Change group details"
        },
        {
          name: "Permissions",
          component: PermissionList,
          icon: "security",
          tooltip: "Manage group permissions"
        }
      ]
    }
  },
  methods: {
    async addGroup() {
      await this.$refs.groupAdd.onSave();
    },
    rootGroups() {
      return this.tree[null]?.map(i => this.groups[i]);
    },
    switchGroup(newGroup) {
      this.activeGroup = newGroup;
    }
  },
  computed: {
    bindArgs() {
      const activeTab = this.$refs.groupTab?.currentTab;
      if (activeTab === 2) {
        return {recipientType: "Group", recipientId: this.activeGroup.id};
      }
      return {group: this.activeGroup};
    }
  }
}
</script>

<style scoped>

</style>