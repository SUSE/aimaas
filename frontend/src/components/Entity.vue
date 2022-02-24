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
import PermissionList from "@/components/auth/PermissionList";

export default {
  name: "Entity",
  components: {BaseLayout, Tabbing},
  inject: ["activeSchema"],
  emits: ["pending-reviews"],
  data() {
    return {
      entity: null,
      tabs: [
        {
          name: 'Show/Edit',
          component: shallowRef(EntityForm),
          icon: "mode_edit",
          tooltip: "Edit/show entity details"
        },
        {
          name: "Permissions",
          component: PermissionList,
          icon: "security",
          tooltip: "Manage permissions on the entity"
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
    title() {
      return this.entity?.name || this.$route.params.entitySlug || '-';
    },
    currentProperties() {
      const currIndex = this.$refs.entitytabbing?.currentTab || 0;
      if (this.tabs[currIndex].component.name === "PermissionList") {
        return {objectType: "Entity", objectId: this.entity?.id};
      }
      let props = {schema: this.activeSchema};

      if (this.tabs[currIndex].component.name === "Changes") {
        props.entitySlug = this.$route.params.entitySlug;
      }

      if (this.tabs[currIndex].component.name === "EntityForm") {
        props.entity = this.entity;
      }

      return props;
    }
  },
  methods: {
    async updateEntity() {
      if (this.$route.params.entitySlug && this.activeSchema) {
        const params = {
          schemaSlug: this.activeSchema.slug,
          entityIdOrSlug: this.$route.params.entitySlug
        };
        this.entity = await this.$api.getEntity(params);
      } else {
        this.entity = null;
      }
    },
    async onUpdate() {
      await this.updateEntity();
    }
  },
  async activated() {
    await this.updateEntity();
  },
  watch: {
    async "$route.params.entitySlug"() {
      await this.updateEntity();
    },
    async activeSchema() {
      await this.updateEntity();
    }
  }
};
</script>