<template>
  <BaseLayout>
    <template v-slot:additional_breadcrumbs>
      <li class="breadcrumb-item active">{{ title }}</li>
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
          name: "History",
          component: shallowRef(Changes),
          icon: 'history',
          tooltip: 'Change history of schema',
          disabled: true
        }
      ],
    }
  },
  inject: ['activeSchema'],
  computed: {
    currentProperties() {
      let props = {schema: this.activeSchema};
      const currIndex = this.$refs.schematabbing?.currentTab || 0;
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
  }
}
</script>
