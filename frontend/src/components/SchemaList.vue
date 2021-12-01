<template>
  <ul class="list-group sticky-top">
    <li
      v-on:click="$emit('selectSchema', schema)"
      v-for="schema in schemas"
      :key="schema.id"
      class="list-group-item"
      :class="this.selectedSchema == schema ? 'active' : ''"
    >
      {{ schema.name }}
    </li>
    <li v-for="index in 30" :key="index" class="list-group-item">An item</li>
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
