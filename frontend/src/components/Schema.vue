<template>
  <BaseLayout>
    <template v-slot:additional_breadcrumbs>
      <li class="breadcrumb-item active">{{ title }}</li>
    </template>
  </BaseLayout>

  <div class="container">
    <ul class="nav nav-tabs" id="schemaTabs" role="tablist">
      <li v-for="tab in tabs" data-bs-toggle="tooltip" :key="tab.name" :title="tab.tooltip"
          class="nav-item">
        <button class="nav-link" :class="currentTab === tab.component ? 'active': ''" type="button"
                v-on:click="currentTab = tab.component">
          <i class='eos-icons'>{{ tab.icon }}</i>
          {{ tab.name }}
        </button>
      </li>
    </ul>
    <div class="tab-content">
      <div class="tab-pane show active border p-2" role="tabpanel">
        <keep-alive>
          <component :is="currentTab" v-bind="currentProperties"></component>
        </keep-alive>
      </div>
    </div>
  </div>
</template>

<script>
import {shallowRef} from "vue";
import BaseLayout from "@/components/layout/BaseLayout";
import EntityList from "@/components/EntityList";
import EntityForm from "@/components/inputs/EntityForm";
import SchemaEdit from "@/components/SchemaEdit";
import Changes from "@/components/change_review/Changes";

export default {
  name: "Schema",
  components: {BaseLayout, EntityList, EntityForm, SchemaEdit},
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
          tooltip: 'Change history of schema'
        }
      ],
      currentTab: shallowRef(EntityList)
    }
  },
  inject: ['activeSchema'],
  computed: {
    currentProperties() {
      let props = {schema: this.activeSchema};
      if (this.currentTab.name === EntityList.name) {
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
