<template>
  <BaseLayout>
    <template v-slot:additional_breadcrumbs>
      <li class="breadcrumb-item">
        <router-link :to="{name: 'schema-view', params: {schemaSlug: activeSchema?.slug}}">
          {{ activeSchema?.name || 'n/a' }}
        </router-link>
      </li>
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
        <component :is="currentTab" v-bind="currentProperties" @update="onUpdate"/>
      </div>
    </div>
  </div>
</template>

<script>
import {shallowRef} from "vue";
import BaseLayout from "@/components/layout/BaseLayout";
import EntityForm from "@/components/inputs/EntityForm";
import Changes from "@/components/change_review/Changes";

export default {
  name: "Entity",
  components: {EntityForm, BaseLayout},
  inject: ["activeSchema"],
  data() {
    return {
      title: '',
      tabs: [
        {
          name: 'Show/Edit',
          component: shallowRef(EntityForm),
          icon: "mode_edit",
          tooltip: "Edit/show entity details"
        },
        {
          name: "History",
          component: shallowRef(Changes),
          icon: "history",
          tooltip: 'Change history of entity'
        }
      ],
      currentTab: shallowRef(EntityForm)
    };
  },
  computed: {
    currentProperties() {
      let props = {schema: this.activeSchema};
      if (this.currentTab.name === Changes.name) {
        props.entitySlug = this.$route.params.entitySlug;
      }
      return props;
    }
  },
  methods: {
    onUpdate(d) {
      this.title = d.name || 'New';
    }
  }
};
</script>