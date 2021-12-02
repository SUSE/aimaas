<template>
  <RouterLink :to="value.link">{{ value.name }}</RouterLink>
</template>

<script>
export default {
  name: "ValueReference",
  props: ["value"],
};
</script>
