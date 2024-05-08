<template>
  <Placeholder :big="true" :loading="loading">
    <template v-slot:content>
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
      <Tabbing :bind-args="bindArgs" :tabs="tabs" :tabEvents="{update: onUpdate}"/>
    </template>
  </Placeholder>
</template>

<script setup>
import {markRaw, ref, computed, watch} from "vue";
import BaseLayout from "@/components/layout/BaseLayout";
import EntityForm from "@/components/inputs/EntityForm";
import Changes from "@/components/change_review/Changes";
import Tabbing from "@/components/layout/Tabbing";
import PermissionList from "@/components/auth/PermissionList";
import EntityBulkAdd from "@/components/EntityBulkAdd";
import Placeholder from "@/components/layout/Placeholder";
import {useSchema} from "@/composables/schema";
import {useRoute} from "vue-router";
import {api} from "@/composables/api";

const {getSchema, activeSchema} = useSchema();
const route = useRoute();
const entity = ref(null);
const loading = ref(true);
const tabs = ref([
  {
    name: 'Show/Edit',
    component: markRaw(EntityForm),
    icon: "mode_edit",
    tooltip: "Edit/show entity details"
  },
  {
    name: "Bulk Add (copy Attributes)",
    component: markRaw(EntityBulkAdd),
    icon: "add_circle",
    tooltip: "Copy over entity attributes to new entities"
  },
  {
    name: "Permissions",
    component: markRaw(PermissionList),
    icon: "security",
    tooltip: "Manage permissions on the entity"
  },
  {
    name: "History",
    component: markRaw(Changes),
    icon: "history",
    tooltip: 'Change history of entity'
  }
]);

const title = computed(() => {
  return entity.value?.name || route.params.entitySlug || '-';
});
const bindArgs = computed(() => {
  return [
    {schema: activeSchema.value, entity: entity.value},
    {schema: activeSchema.value, entity: entity.value},
    {objectType: "Entity", objectId: entity.value?.id},
    {schema: activeSchema.value, entitySlug: route.params.entitySlug},
  ]
});

async function getEntity() {
  if (route.params.entitySlug && route.params.schemaSlug) {
    const params = {
      schemaSlug: route.params.schemaSlug,
      entityIdOrSlug: route.params.entitySlug
    };
    entity.value = await api.getEntity(params);
  } else {
    entity.value = null;
  }
}

async function onUpdate(editEntity) {
  if (editEntity) {
    entity.value = editEntity;
  }
}

watch(entity, (newValue) => {
  if (newValue?.name) {
    document.title = newValue.name;
  }
});
watch(
    route,
    () => {
      loading.value = true;
      Promise.all([getSchema(), getEntity()])
          .then(() => loading.value = false);
    },
    {
      immediate: true
    }
);
</script>
