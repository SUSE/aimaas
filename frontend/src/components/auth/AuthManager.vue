<template>
  <BaseLayout>
    <template v-slot:additional_breadcrumbs>
      <li class="breadcrumb-item active">User Management</li>
    </template>
  </BaseLayout>

  <Tabbing :bind-args="currentProperties" :tabs="tabs" ref="admtabbing"/>
</template>

<script>
import {shallowRef} from "vue";
import BaseLayout from "@/components/layout/BaseLayout";
import GroupManager from "@/components/auth/GroupManager";
import Tabbing from "@/components/layout/Tabbing";

export default {
  name: "AuthManager",
  components: {Tabbing, BaseLayout},
  data() {
    return {
      groups: {},
      users: {},
      tree: {},
      activeGroup: null,
      tabs: [
        {
          name: "Groups",
          component: shallowRef(GroupManager),
          icon: "groups",
          tooltip: "Manage groups"
        }
      ]
    };
  },
  async created() {
    await this.loadData();
  },
  computed: {
    currentProperties() {
      const currIndex = this.$refs.admtabbing?.currentTab || 0;
      let props = {};

      if (this.tabs[currIndex].component.name === "GroupManager") {
        props.groups = this.groups;
        props.tree = this.tree;
        props.users = this.users;
      }

      return props;
    }
  },
  methods: {
    async loadData() {
      // Load group data
      let response = await this.$api.getGroups();
      for (const group of response) {
        this.groups[group.id] = group;
        if (!(group.parent_id in this.tree)) {
          this.tree[group.parent_id] = [];
        }
        this.tree[group.parent_id].push(group.id);
      }

      // Load user data
      response = await this.$api.getUsers();
      for (const user of response) {
        this.users[user.id] = user;
      }
    },

  }
}
</script>

<style scoped>

</style>