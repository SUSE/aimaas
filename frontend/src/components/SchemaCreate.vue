<template>
  <BaseLayout>
    <template v-slot:additional_breadcrumbs>
      <li class="breadcrumb-item active">Create new schema</li>
    </template>
  </BaseLayout>

  <div class="container">
    <SchemaEdit :schema="null"/>
  </div>
</template>


<script>
import BaseLayout from "@/components/layout/BaseLayout.vue";
import SchemaEdit from "@/components/SchemaEdit.vue";

export default {
  name: "SchemaCreate",
  components: {BaseLayout, SchemaEdit}
};
</script>
