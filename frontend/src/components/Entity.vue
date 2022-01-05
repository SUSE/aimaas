<template>
  <BaseLayout>
    <template v-slot:additional_breadcrumbs>
      <li class="breadcrumb-item">
        <router-link :to="{name: 'schema-view', params: {schemaSlug: activeSchema?.slug || 'n-a'}}">
          {{ activeSchema?.name || 'n/a' }}
        </router-link>
      </li>
      <li class="breadcrumb-item active">{{ title }}</li>
    </template>
  </BaseLayout>
  <Tabbing :bind-args="currentProperties" :tabs="tabs" ref="entitytabbing"
           :tabEvents="{update: onUpdate}"/>
</template>

<script>
import {shallowRef} from "vue";
import BaseLayout from "@/components/layout/BaseLayout";
import EntityForm from "@/components/inputs/EntityForm";
import Changes from "@/components/change_review/Changes";
import Tabbing from "@/components/layout/Tabbing";

export default {
  name: "Entity",
  components: {BaseLayout, Tabbing},
  inject: ["activeSchema"],
  emits: ["pending-reviews"],
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
      ]
    };
  },
  computed: {
    currentProperties() {
      const currIndex = this.$refs.entitytabbing?.currentTab || 0;
      let props = {schema: this.activeSchema};

      if (this.tabs[currIndex].component.name === "Changes") {
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