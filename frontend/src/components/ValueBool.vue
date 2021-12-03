<template>
  <template v-if="value === true"><CheckIcon /></template>
  <template v-else-if="value === false"><CircleXIcon /></template>
  <template v-else>N/A</template>
</template>

<script>
import CheckIcon from "./CheckIcon.vue";
import CircleXIcon from "./CircleXIcon.vue";

export default {
  name: "ValueBool",
  props: ["value"],
  components: { CheckIcon, CircleXIcon },
};
</script>
