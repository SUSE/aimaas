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
    <template v-slot:actions>
      <div v-if="entity?.deleted" class="alert alert-danger p-2">
        <i class="eos-icons me-2">delete</i>
        This entity is deleted.
    </div>
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
import EntityBulkAdd from "@/components/EntityBulkAdd.vue";

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
          name: "Bulk Add (copy Attributes)",
          component: shallowRef(EntityBulkAdd),
          icon: "add_circle",
          tooltip: "Copy over entity attributes to a new entities"
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
      const tabPropsMap = {
        'EntityForm': {schema: this.activeSchema, entity: this.entity},
        'EntityBulkAdd': {schema: this.activeSchema, attributes: this.entity},
        'PermissionList': {objectType: "Entity", objectId: this.entity?.id},
        'Changes': {schema: this.activeSchema, entitySlug: this.$route.params.entitySlug},
      }

      return tabPropsMap[this.tabs[currIndex].component.name];
    }
  },
  methods: {
    async getEntity() {
      if (this.$route.params.entitySlug && this.$route.params.schemaSlug) {
        const params = {
          schemaSlug: this.$route.params.schemaSlug,
          entityIdOrSlug: this.$route.params.entitySlug
        };
        this.entity = await this.$api.getEntity(params);
      } else {
        this.entity = null;
      }
    },
    async onUpdate(entity) {
      if (entity) {
        this.entity = entity;
      }
    }
  },
  async activated() {
    await this.getEntity();
  },
  watch: {
    entity(newValue) {
      if (newValue?.name) {
        document.title = newValue.name;
      }
    },
    $route: {
      handler: "getEntity",
      immediate: true
    },
  }
};
</script>
