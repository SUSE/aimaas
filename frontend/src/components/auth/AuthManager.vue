<template>
  <BaseLayout>
    <template v-slot:additional_breadcrumbs>
      <li class="breadcrumb-item active">User Management</li>
    </template>
  </BaseLayout>

  <Tabbing :bind-args="{}" :tabs="tabs" ref="admtabbing"/>
</template>

<script>
import {computed, shallowRef} from "vue";
import BaseLayout from "@/components/layout/BaseLayout";
import GroupManager from "@/components/auth/GroupManager";
import UserManager from "@/components/auth/UserManager";
import Tabbing from "@/components/layout/Tabbing";
import {loadGroupData, loadUserData} from "@/composables/auth";

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
        },
        {
          name: "Users",
          component: shallowRef(UserManager),
          icon: "person",
          tooltip: "Manage users"
        }
      ]
    };
  },
  provide() {
    return {
      groups: computed(() => this.groups),
      users: computed(() => this.users),
      tree: computed(() => this.tree)
    }
  },
  async created() {
    await this.loadData();
  },
  methods: {
    async loadData() {
      [this.groups, this.tree] = await loadGroupData(this.$api);
      this.users = await loadUserData(this.$api);
    },

  }
}
</script>

<style scoped>

</style>