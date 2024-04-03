<template>
  <h5>User Details</h5>
  <div class="row">
    <div class="col-3 fw-bold">Username:</div>
    <div class="col-9">{{ user?.username }}</div>
  </div>
  <div class="row">
    <div class="col-3 fw-bold">Name:</div>
    <div class="col-9">{{ user?.firstname }} {{ user?.lastname }}</div>
  </div>
  <div class="row">
    <div class="col-3 fw-bold">Email:</div>
    <div class="col-9">
      <a :href="`mailto:${user?.email}`">{{ user?.email }}</a>
    </div>
  </div>
  <div class="row">
    <div class="col-3 fw-bold">Is Active?</div>
    <div class="col-9 d-flex flex-row justify-content-between flex-grow-0">
      <div>
        <span
          class="badge"
          :class="
            user?.is_active ? 'bg-success text-black' : 'bg-dark text-light'
          "
        >
          {{ user?.is_active ? "Yes" : "No" }}
        </span>
      </div>
      <button
        class="btn"
        @click="onClick"
        :class="`btn-outline-${user?.is_active ? 'danger' : 'primary'}`"
      >
        <i class="eos-icons me-1">
          {{ user?.is_active ? "block" : "play_arrow" }}
        </i>
        {{ user?.is_active ? "Deactivate" : "Activate" }}
      </button>
    </div>
  </div>
  <h5>Group memberships</h5>
  <Suspense v-if="user">
    <GroupMemberships :username="user.username" />
    <template #fallback>
      <Placeholder />
    </template>
  </Suspense>
</template>

<script>
import Placeholder from "@/components/layout/Placeholder";
import GroupMemberships from "@/components/auth/GroupMemberships";
import { useAuthStore } from "@/store/auth";

export default {
  name: "UserDetails",
  components: { Placeholder, GroupMemberships },
  props: {
    user: {
      required: false,
      type: Object,
    },
  },
  setup() {
    const { activateUser, deactivateUser } = useAuthStore();
    return { activateUser, deactivateUser };
  },
  methods: {
    async onClick() {
      if (this.user === null) {
        return;
      }
      if (this.user?.is_active) {
        await this.deactivateUser(this.user.username);
      } else {
        await this.activateUser(this.user.username);
      }
    },
  },
};
</script>

<style scoped></style>
