<template>
  <Placeholder :big="true" :loading="loading">
    <template v-slot:content>
      <BaseLayout>
        <template v-slot:additional_breadcrumbs>
          <li class="breadcrumb-item active">
            <router-link :to="{name: 'schema-view', params: {schemaSlug: activeSchema?.slug || 'n-a'}}">
              {{ activeSchema?.name || 'n/a' }}
            </router-link>
          </li>
          <li class="breadcrumb-item active">Bulk Editor</li>
        </template>
      </BaseLayout>
      <div v-for="e of entities" :key="e.id" class="border mb-3 p-2">
        <EntityForm :entity="e" :schema="activeSchema"
                    :batch-mode="true" :ref="el => { entityFormRefs[`e_form_${e.id}`] = el }"
                    v-on:save-all="saveAll"/>
      </div>
    </template>
  </Placeholder>
</template>

<script setup>
import BaseLayout from "@/components/layout/BaseLayout.vue";
import EntityForm from "@/components/inputs/EntityForm.vue";
import Placeholder from "@/components/layout/Placeholder.vue";
import {ref, computed, watch} from "vue";
import {useSchema} from "@/composables/schema";
import {useRoute} from "vue-router";
import {api} from "@/composables/api";
import {alertStore} from "@/composables/alert";

const {getSchema, activeSchema} = useSchema();
const route = useRoute();
const entities = ref([]);
const loading = ref(true);
const entityFormRefs = ref([]);

const entityIds = computed(() => {
  return entities.value.map(x => x.id);
});

async function getEntityData() {
  const schemaSlug = route.params.schemaSlug;
  if (!schemaSlug) {
    return
  }

  const queryIds = (route.query?.entity || []);
  entities.value = entities.value.filter(x => queryIds.includes(x.id));
  const promises = queryIds
      .map(x => parseInt(x))
      .filter(x => !entityIds.value.includes(x))
      .map(x => api.getEntity({schemaSlug: schemaSlug, entityIdOrSlug: x}));
  Promise.all(promises).then(x => {
    entities.value = entities.value.concat(x);
  });
}

async function saveAll() {
  const promises = Object.entries(entityFormRefs.value)
      .map(x => x[1].updateEntity());
  Promise.all(promises).then(x => {
    if (x.every(y => y === null)) {
      alertStore.push(
          "warning",
          "None of the entities were changed. Therefore no changes were sent to server."
      );
    }
  });
}

watch(
    route,
    () => {
      loading.value = true;
      Promise.all([getSchema(), getEntityData()])
          .then(() => loading.value = false);
    },
    {
      immediate: true,
      deep: true
    }
);
</script>
