<template>
  <ul class="list-group">
    <li class="list-group-item" v-for="group in memberships" :key="group.id">
      {{ group.name }}
    </li>
    <li v-if="memberships.length === 0" class="list-group-item p-0">
      <div class="alert alert-info text-center m-0">
        Not a member of any group.
      </div>
    </li>
  </ul>
</template>
<script setup>
import { api } from "@/composables/api";
import { onActivated } from "vue";

const props = defineProps(["username"]);
const memberships = await api.getUserMemberships({ username: props.username });

onActivated(async () => {
  memberships.value = await api.getUserMemberships({ username: props.username });
})
</script>
