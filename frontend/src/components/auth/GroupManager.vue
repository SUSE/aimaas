<template>
  <div class="row m-0">
      <ul class="list-group col-md-3">
        <GroupListItem :group="group" :groups="groups" :tree="tree"
                       v-for="group in rootGroups()" :key="group.id"
                       @groupSelected="switchGroup"/>
      </ul>
      <div class="col-md-9">
        <Tabbing :tabs="tabs" :bind-args="{group: activeGroup, users: users}"/>
      </div>
    </div>

</template>

<script>
import GroupMembers from "@/components/auth/GroupMembers";
import GroupListItem from "@/components/auth/GroupListItem";
import Tabbing from "@/components/layout/Tabbing";

export default {
  name: "GroupManager",
  components: {Tabbing, GroupListItem},
  props: {
    groups: {
      required: true,
      type: Object
    },
    tree: {
      required: true,
      type: Object
    },
    users: {
      required: true,
      type: Object
    }
  },
  data() {
    return {
      activeGroup: null,
      tabs: [
          {
          name: "Members",
          component: GroupMembers,
          icon: "groups",
          tooltip: "Manage group members"
        },
      ]
    }
  },
  methods: {
    rootGroups() {
      return this.tree[null]?.map(i => this.groups[i]);
    },
    switchGroup(newGroup) {
      this.activeGroup = newGroup;
    }
  }
}
</script>

<style scoped>

</style>