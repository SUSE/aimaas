<template>
  <ul class="list-group sticky-top">
    <li
      v-on:click="$emit('selectSchema', schema)"
      v-for="schema in schemas"
      :key="schema.id"
      class="list-group-item"
      :class="selectedSchema === schema ? 'active' : ''"
    >
      {{ schema.name }}
    </li>
  </ul>
</template>

<script>
export default {
  name: "SchemaList",
  props: ["schemas", "selectedSchema"],
  emits: ["selectSchema"],
  computed: {},
  methods: {},
};
</script>
