<template>
  <BaseLayout>
    <template v-slot:additional_breadcrumbs>
      <li class="breadcrumb-item">{{ activeSchema?.name || 'n/a' }}</li>
      <li class="breadcrumb-item active">{{ title }}</li>
    </template>
  </BaseLayout>
  <EntityForm @update="onUpdate"/>
</template>

<script>
import BaseLayout from "@/components/layout/BaseLayout";
import EntityForm from "@/components/inputs/EntityForm";


export default {
  name: "EntityEdit",
  components: {EntityForm, BaseLayout},
  inject: ["activeSchema"],
  data() {
    return {title: ''};
  },
  methods: {
    onUpdate(d) {
      this.title = d.name || 'New';
    }
  }
};
</script>