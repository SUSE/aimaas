<template>
  <label v-if="label">
    {{ label }}
  </label>
  <input
    class="form-control"
    type="text"
    :value="modelValue"
    @input="onInput"
    placeholder="enter entity name"
  />
  <ul class="list-group">
    <li
      v-for="(e, index) in foundEntities"
      :key="index"
      class="list-group-item"
    >
      <RouterLink :to="`/${schemaSlug}/${e.slug}`">{{ e.name }}</RouterLink>
      <template v-if="e.slug != modelValue?.slug"
        ><button
          @click="this.$emit('selected', e)"
          type="button"
          class="ms-1 btn btn-sm btn-outline-primary"
        >
          Choose
        </button></template
      >
      <template v-else><small class="ms-1">Chosen option</small></template>
    </li>
  </ul>
</template>

<script>
export default {
  name: "ReferencedEntitySelect",
  emits: ["changed", "selected", "update:modelValue"],
  props: ["label", "modelValue", "foundEntities", "schemaSlug"],
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
      this.$emit("changed");
    },
  },
};
</script>