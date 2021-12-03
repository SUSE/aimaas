<template>
  {{ value ? new Date(value).toUTCString() : "N/A" }}
</template>

<script>
export default {
  name: "ValueDateTime",
  props: ["value"],
};
</script>
