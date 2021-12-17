<template>
  <BaseInput :label="label" :args="args" :vertical="vertical">
    <template v-slot:field>
      <input
          class="form-control"
          type="text"
          :value="modelValue"
          @input="onInput"
          placeholder="enter entity name"
          v-bind="args"
      />
      <ul class="list-group">
        <li
            v-for="(e, index) in foundEntities"
            :key="index"
            class="list-group-item"
        >
          <RouterLink :to="`/${schemaSlug}/${e.slug}`">{{ e.name }}</RouterLink>
          <template v-if="e.slug != modelValue?.slug"
          >
            <button
                @click="this.$emit('selected', e)"
                type="button"
                class="ms-1 btn btn-sm btn-outline-primary"
            >
              Choose
            </button>
          </template
          >
          <template v-else><small class="ms-1">Chosen option</small></template>
        </li>
      </ul>
    </template>
  </BaseInput>
</template>

<script>
import BaseInput from "@/components/layout/BaseInput";

export default {
  name: "ReferencedEntitySelect",
  components: {BaseInput},
  emits: ["changed", "selected", "update:modelValue"],
  props: ["args", "label", "modelValue", "foundEntities", "schemaSlug", "vertical"],
  methods: {
    onInput(event) {
      this.$emit("update:modelValue", event.target.value);
      this.$emit("changed");
    },
  },
};
</script>