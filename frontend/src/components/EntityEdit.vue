<template>
  <h2>Edit entity</h2>
  <div v-if="schema != null">
    <EntityCreateEditForm
      @submit="this.sendBody"
      :schema="this.schema"
      :entity="this.entity"
    />
  </div>
</template>

<script>
import EntityCreateEditForm from "./EntityCreateEditForm.vue";
import _isEqual from "lodash/isEqual";
import { api } from "../api";

export default {
  name: "EntityEdit",
  emits: [],
  components: { EntityCreateEditForm },
  async created() {
    this.entity = await (
      await api.getEntity({
        schemaSlug: this.$route.params.schemaSlug,
        entityIdOrSlug: this.$route.params.entitySlug,
      })
    ).json();

    this.schema = await (
      await api.getSchema({ slugOrId: this.$route.params.schemaSlug })
    ).json();
  },
  computed: {},
  data() {
    return {
      entity: null,
      schema: null,
    };
  },
  methods: {
    leaveOnlyChangedFields(body) {
      const result = {};
      for (const [attr, value] of Object.entries(body)) {
        if (!_isEqual(value, this.entity[attr])) {
          result[attr] = value;
        }
      }
      return result;
    },

    async sendBody(body) {
      body = this.leaveOnlyChangedFields(body);
      if (Object.keys(body).length == 0) return;

      const resp = await api.updateEntity({
        schemaSlug: this.$route.params.schemaSlug,
        entityIdOrSlug: this.$route.params.entitySlug,
        body: body,
      });
      if (resp.status == 200) {
        this.$router.push(
          `/${this.schema.slug}/${body.slug || this.entity.slug}`
        );
      }
    },
  },
};
</script>