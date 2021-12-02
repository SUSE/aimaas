<template >
  <template v-if="this.entity">
    <div class="row">
      <div class="col-9">
        <h2>{{ this.entity.name }}</h2>
        <p>
          <small>{{ this.entity.slug }}</small>
        </p>
      </div>
      <div class="col">
        <router-link
          :to="`/edit/${this.$route.params.schemaSlug}/${$route.params.entityIdOrSlug}`"
          class="btn btn-sm btn-primary mt-3"
          style="text-decoration: none"
          >Edit entity</router-link
        >
      </div>
    </div>

    <div class="row">
      
      <div class="col-9">
        <table class="table table-bordered table-sm">
          <tbody>
            <tr v-for="key in Object.keys(this.displayFields)" :key="key">
              
              <td class="col-3">{{ key }}</td>
              
              <td class="col-9" v-if="!this.fieldsInfo[key].list">
                <component
                  :is="this.fieldsInfo[key].component"
                  :value="this.entity[key]"
                ></component>
              </td>

              <td v-else class="col-9">
                <ul>
                  <li v-for="(item, index) in this.entity[key]" :key="index">
                    <component
                      :is="this.fieldsInfo[key].component"
                      :value="item"
                    ></component>
                  </li>
                </ul>
              </td>

            </tr>
          </tbody>
        </table>
      </div>

      <div class="col-3">
        <RecentChangesSidebar
          :schemaSlug="this.$route.params.schemaSlug"
          :entitySlug="this.entity.slug"
        />
      </div>

    </div>
  </template>
  <template v-else>Nothing to show here</template>
</template>

<script>
import { getFieldsInfo } from "../utils";
import { api } from "../api";
import RecentChangesSidebar from "./RecentChangesSidebar.vue";
import ValueString from "./ValueString.vue";
import ValueBool from "./ValueBool.vue";
import ValueReference from "./ValueReference.vue";
import ValueDateTime from "./ValueDateTime.vue";


export default {
  name: "EntityDetail",
  components: {
    RecentChangesSidebar,
    ValueString,
    ValueBool,
    ValueReference,
    ValueDateTime,
  },
  watch: {
    $route: {
      handler: "initFetch",
      immediate: true, // runs immediately with mount() instead of calling method on mount hook
    },                // we need this because we can go to other entity within this component
  },                 // but on other schema; without this schema doesn't update
  computed: {
    displayFields() {
      const { id, slug, name, deleted, ...other } = this.entity;
      id, slug, name, deleted;
      return other;
    },
  },
  data() {
    return {
      entity: null,
      meta: null,
      fieldsInfo: null,
      key: this.$route.path,
    };
  },
  methods: {
    async initFetch() {
      const data = await this.fetchEntityDetails(
        this.$route.params.schemaSlug,
        this.$route.params.entityIdOrSlug
      );
      const { meta, ...entity } = data;
      this.meta = meta;
      this.fieldsInfo = getFieldsInfo(meta.fields);

      for (const [field, props] of Object.entries(meta.fields)) {
        if (props.type == "FK") {
          await this.populateReferencedEntities({
            entity,
            field,
            schemaSlug: props.bind_to_schema,
            referenceIdOrSlug: entity[field],
            list: props.list,
          });
        }
      }

      this.entity = entity;
    },

    async populateReferencedEntities({
      entity,
      field,
      schemaSlug,
      referenceIdOrSlug,
      list,
    }) {
      if (!list) {
        const e = await this.fetchEntity({
          schemaSlug: schemaSlug,
          entityIdOrSlug: referenceIdOrSlug,
        });
        entity[field] = {
          name: e.name,
          link: `/${schemaSlug}/${e.slug}`,
        };
      } else {
        entity[field] = await Promise.all(
          referenceIdOrSlug.map(async (idOrSlug) => {
            const e = await this.fetchEntity({
              schemaSlug: schemaSlug,
              entityIdOrSlug: idOrSlug,
            });
            return {
              name: e.name,
              link: `/${schemaSlug}/${e.slug}`,
            };
          })
        );
      }
    },

    async fetchEntityDetails(schemaSlug, entityIdOrSlug) {
      const response = await api.getEntity({
        schemaSlug: schemaSlug,
        entityIdOrSlug: entityIdOrSlug,
        meta: true,
      });
      const json = await response.json();
      return json;
    },

    async fetchEntity({ schemaSlug, entityIdOrSlug }) {
      const response = await api.getEntity({
        schemaSlug: schemaSlug,
        entityIdOrSlug: entityIdOrSlug,
      });

      const json = await response.json();
      return json;
    },
  },
};
</script>
