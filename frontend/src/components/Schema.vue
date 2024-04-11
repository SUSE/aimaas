<template>
  <BaseLayout>
    <template v-slot:additional_breadcrumbs>
      <li class="breadcrumb-item active">{{ title }}</li>
    </template>
    <template v-slot:actions>
      <div v-if="activeSchema?.deleted" class="alert alert-danger p-2">
        <i class="eos-icons me-2">delete</i>
        This schema is deleted.
    </div>
    </template>
  </BaseLayout>

  <Tabbing :bind-args="bindArgs" :tabs="tabs" ref="schematabbing"/>

</template>

<script>
import { markRaw } from "vue";
import BaseLayout from "@/components/layout/BaseLayout";
import EntityList from "@/components/EntityList";
import EntityForm from "@/components/inputs/EntityForm";
import SchemaEdit from "@/components/SchemaEdit";
import Changes from "@/components/change_review/Changes";
import Tabbing from "@/components/layout/Tabbing";
import PermissionList from "@/components/auth/PermissionList";

export default {
  name: "Schema",
  components: {BaseLayout, Tabbing},
  data: function () {
    return {
      tabs: [
        {
          name: "Entities",
          component: markRaw(EntityList),
          icon: "table_view",
          tooltip: "Show entities"
        },
        {
          name: "Edit / Show",
          component: markRaw(SchemaEdit),
          icon: "mode_edit",
          tooltip: "Edit/Show schema structure"
        },
        {
          name: "Add Entity",
          component: markRaw(EntityForm),
          icon: 'add_circle',
          tooltip: 'Add new entity'
        },
        {
          name: "Permissions",
          component: markRaw(PermissionList),
          icon: "security",
          tooltip: "Manage permissions on the schema"
        },
        {
          name: "History",
          component: markRaw(Changes),
          icon: 'history',
          tooltip: 'Change history of schema'
        }
      ],
    }
  },
  inject: ['activeSchema'],
  computed: {
    bindArgs() {
      return [
        { schema: this.activeSchema, advancedControls: true },
        { schema: this.activeSchema },
        { schema: this.activeSchema },
        { objectType: "Schema", objectId: this.activeSchema?.id },
        { schema: this.activeSchema },
      ]
    },
    title() {
      try {
        return this.activeSchema.name;
      } catch (e) {
        return "n/a";
      }
    }
  },
  updated() {
    if (this.activeSchema?.name) {
        document.title = this.activeSchema.name;
      }
  }
}
</script>
