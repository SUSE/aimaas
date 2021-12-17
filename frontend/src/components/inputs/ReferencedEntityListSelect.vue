<template>
  <BaseInput :label="label" :args="args" :vertical="vertical">
    <template v-slot:field>
      <input class="form-control" type="text" :value="modelValue" @input="onInput"
             placeholder="enter entity name" v-bind="args"/>
      <ul class="list-group">
        <li
            v-for="(e, index) in foundEntities"
            :key="index"
            class="list-group-item"
        >
          <RouterLink :to="`/${schemaSlug}/${e.slug}`">{{ e.name }}</RouterLink>
          <template v-if="!selected(e.slug)"
          >
            <button
                @click="
            this.$emit('select', { name: e.name, slug: e.slug, id: e.id })
          "
                type="button"
                class="ms-1 btn btn-sm btn-outline-primary"
            >
              Add
            </button>
          </template
          >
          <template v-else><small class="ms-1">Already added</small></template>
        </li>
      </ul>

      <p>Added items</p>
      <ul class="list-group">
        <li
            v-for="(entity, index) in this.selectedEntities"
            :key="index"
            class="list-group-item"
        >
          <RouterLink :to="`/${schemaSlug}/${entity.slug}`">{{
              entity.name
            }}
          </RouterLink>
          <button
              @click="this.$emit('unselect', index)"
              type="button"
              class="btn btn-sm btn-outline-secondary ms-1"
          >
            Remove
          </button>
        </li>
      </ul>
    </template>
  </BaseInput>
</template>

<script>
import BaseInput from "@/components/layout/BaseInput";

export default {
  name: "ReferencedEntityListSelect",
  components: {BaseInput},
  props: [
    "args",
    "label",
    "modelValue",
    "foundEntities",
    "schemaSlug",
    "selectedEntities",
    "vertical"
  ],
  emits: ["changed", "select", "unselect", "update:modelValue"],
  computed: {
    selectedSlugs() {
      return this.selectedEntities.map((x) => x.slug);
    },
  },
  methods: {
    selected(slug) {
      return this.selectedSlugs.includes(slug);
    },
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
      this.$emit("changed");
    },
  },
};
</script>