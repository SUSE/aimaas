<template>
  <Placeholder :big="true" :loading="loading">
    <template v-slot:content>
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
      <Tabbing :bind-args="bindArgs" :tabs="tabs"
               :tabEvents="{updateSchema: onSchemaUpdate}"/>
    </template>
  </Placeholder>
</template>

<script setup>
import {markRaw, ref, computed, watch, onUpdated} from "vue";
import BaseLayout from "@/components/layout/BaseLayout";
import EntityList from "@/components/EntityList";
import EntityForm from "@/components/inputs/EntityForm";
import SchemaEdit from "@/components/SchemaEdit";
import Changes from "@/components/change_review/Changes";
import Tabbing from "@/components/layout/Tabbing";
import PermissionList from "@/components/auth/PermissionList";
import Placeholder from "@/components/layout/Placeholder";
import {useSchema} from "@/composables/schema";
import {useRoute} from "vue-router";

const {getSchema, activeSchema} = useSchema();
const route = useRoute();
const loading = ref(true);
const tabs = ref([
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
]);

const bindArgs = computed(() => {
  return [
    {schema: activeSchema.value, advancedControls: true},
    {schema: activeSchema.value},
    {schema: activeSchema.value},
    {objectType: "Schema", objectId: activeSchema.value?.id},
    {schema: activeSchema.value},
  ]
});
const title = computed(() => {
  return activeSchema.value?.name || "n/a";
});

onUpdated(() => {
  if (activeSchema.value?.name) {
    document.title = activeSchema.value.name;
  }
});

function init() {
  loading.value = true;
  getSchema().then(() => loading.value = false);
}

function onSchemaUpdate() {
  init();
}

watch(
    route,
    () => init(),
    {
      immediate: true
    }
);

</script>