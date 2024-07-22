<template>
  <BaseLayout>
    <template v-slot:additional_breadcrumbs>
      <li class="breadcrumb-item active">User Management</li>
    </template>
  </BaseLayout>
  <Tabbing :tabs="tabs" ref="admtabbing" />
</template>

<script setup>
import { markRaw } from "vue";
import BaseLayout from "@/components/layout/BaseLayout.vue";
import GroupManager from "@/components/auth/GroupManager.vue";
import UserManager from "@/components/auth/UserManager.vue";
import Tabbing from "@/components/layout/Tabbing.vue";

const tabs = [
  {
    name: "Groups",
    component: markRaw(GroupManager),
    icon: "groups",
    tooltip: "Manage groups",
  },
  {
    name: "Users",
    component: markRaw(UserManager),
    icon: "person",
    tooltip: "Manage users",
  },
];
</script>
