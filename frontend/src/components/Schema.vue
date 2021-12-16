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
          <component v-bind:is="currentTab" :schema="this.activeSchema"></component>
        </keep-alive>
      </div>
    </div>
  </div>
</template>

<script>
import BaseLayout from "@/components/layout/BaseLayout";
import EntityList from "@/components/EntityList";
import SchemaEdit from "@/components/SchemaEdit";

export default {
  name: "Schema",
  components: {BaseLayout, EntityList, SchemaEdit},
  data: function () {
    return {
      tabs: [
        {
          name: "Entities",
          component: EntityList,
          icon: "table_view",
          tooltip: "Show entities"
        },
        {
          name: "Edit / Show",
          component: SchemaEdit,
          icon: "mode_edit",
          tooltip: "Edit/Show schema structure"
        }
      ],
      currentTab: EntityList
    }
  },
  inject: ['activeSchema'],
  computed: {
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
