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

  <Tabbing :bind-args="currentProperties" :tabs="tabs" ref="schematabbing"/>

</template>

<script>
import {shallowRef} from "vue";
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
          component: shallowRef(EntityList),
          icon: "table_view",
          tooltip: "Show entities"
        },
        {
          name: "Edit / Show",
          component: shallowRef(SchemaEdit),
          icon: "mode_edit",
          tooltip: "Edit/Show schema structure"
        },
        {
          name: "Add Entity",
          component: shallowRef(EntityForm),
          icon: 'add_circle',
          tooltip: 'Add new entity'
        },
        {
          name: "Permissions",
          component: PermissionList,
          icon: "security",
          tooltip: "Manage permissions on the schema"
        },
        {
          name: "History",
          component: shallowRef(Changes),
          icon: 'history',
          tooltip: 'Change history of schema'
        }
      ],
    }
  },
  inject: ['activeSchema'],
  computed: {
    currentProperties() {
      const currIndex = this.$refs.schematabbing?.currentTab || 0;
      if (this.tabs[currIndex].component.name === "PermissionList") {
        return {objectType: "Schema", objectId: this.activeSchema.id};
      }

      const props = {schema: this.activeSchema};

      if (this.tabs[currIndex].component.name === "EntityList") {
        props.advancedControls = true;
      }
      return props;
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
