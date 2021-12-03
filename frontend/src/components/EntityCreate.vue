<template>
  <h2>Create new entity</h2>
  <div v-if="schema != null">
    <EntityCreateEditForm @submit="this.sendBody" :schema="this.schema" />
  </div>
</template>


<script>
import EntityCreateEditForm from "./EntityCreateEditForm.vue";
import { api } from "../api";

export default {
  name: "EntityCreate",
  props: [],
  components: { EntityCreateEditForm },
  async created() {
    const schema = await (
      await api.getSchema({ slugOrId: this.$route.params.schemaSlug })
    ).json();
    this.schema = schema;
  },
  methods: {
    async sendBody(body) {
      const resp = await api.createEntity({
        schemaSlug: this.$route.params.schemaSlug,
        body: body,
      });
      if (resp.status == 200) {
        this.$router.push(`/${this.$route.params.schemaSlug}/${body.slug}`);
      }
    },
  },
  computed: {},
  data() {
    return {
      schema: null,
    };
  },
};
</script>