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
import BaseLayout from "@/components/layout/BaseLayout";
import GroupManager from "@/components/auth/GroupManager";
import UserManager from "@/components/auth/UserManager";
import Tabbing from "@/components/layout/Tabbing";

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
