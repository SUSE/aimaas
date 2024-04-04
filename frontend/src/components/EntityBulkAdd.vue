<template>
  <div v-for="num in entityFormComponentsCountRange" :key="`ef-${num}`">
    <EntityForm :ref="`entity-form-${num}`" :schema="schema"
                :attributes="attributes" :batch-mode="true" @save-all="saveAll"/>
  </div>
  <div class="container mt-2">
    <button class="btn btn-outline-secondary w-100" @click="addEntityForm">
      <i class='eos-icons'>add_circle</i>
      Add more
    </button>
  </div>
</template>

<script>
import EntityForm from "@/components/inputs/EntityForm.vue";

export default {
  name: "EntityBulkAdd",
  components: {EntityForm},
  props: {
    schema: {
      type: Object,
      required: true
    },
    attributes: {
      type: Object,
      required: true,
    }
  },
  data() {
    return {
      entityFormComponentCount: 1,
    }
  },
  computed: {
    entityFormComponentsCountRange() {
      return [...Array(this.entityFormComponentCount).keys()];
    },
  },
  methods: {
    async saveAll() {
      const promises = Object.entries(this.$refs)
          .filter(x => x[0].startsWith("entity-form-"))
          .map(x => x[1][0].createEntity());
      await Promise.all(promises);
    },
    addEntityForm() {
      ++this.entityFormComponentCount;
    },
  }
}

</script>

<style scoped>

</style>