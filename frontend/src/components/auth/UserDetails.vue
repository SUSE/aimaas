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
    <div class="col-9"><a :href="`mailto:${user?.email}`">{{ user?.email }}</a></div>
  </div>
  <div class="row">
    <div class="col-3 fw-bold">Is Active?</div>
    <div class="col-9 d-flex flex-row justify-content-between flex-grow-0">
      <div>
        <span class="badge" :class="user?.is_active? 'bg-success text-black': 'bg-dark text-light'">
          {{ user?.is_active ? 'Yes' : 'No' }}
        </span>
      </div>
      <button class="btn" @click="onClick"
              :class="`btn-outline-${user?.is_active? 'danger': 'primary'}`">
        <i class="eos-icons me-1">
          {{ user?.is_active? 'block': 'play_arrow'}}
        </i>
        {{ user?.is_active? 'Deactivate': 'Activate'}}
      </button>
    </div>
  </div>
  <h5>Group memberships</h5>
  <Placeholder :loading="loading">
    <template v-slot:content>
      <ul class="list-group">
        <li class="list-group-item" v-for="group in memberships" :key="group.id">
          {{ group.name }}
        </li>
        <li v-if="memberships.length === 0" class="list-group-item p-0">
          <div class="alert alert-info text-center m-0">Not a member of any group.</div>
        </li>
      </ul>
    </template>
  </Placeholder>
</template>

<script>
import Placeholder from "@/components/layout/Placeholder";

export default {
  name: "UserDetails",
  components: {Placeholder},
  props: {
    user: {
      required: true,
      type: Object
    }
  },
  data() {
    return {
      loading: true,
      memberships: []
    }
  },
  async activated() {
    if (this.user) {
      await this.loadMembership();
    }
  },
  watch: {
    async user() {
      await this.loadMembership();
    }
  },
  methods: {
    async loadMembership() {
      this.loading = true;
      this.memberships = await this.$api.getUserMemberships({username: this.user.username});
      this.loading = false;
    },
    async onClick() {
      if (this.user === null) {
        return;
      }
      if (this.user?.is_active) {
        await this.$api.deactivate_user({username: this.user.username});
      } else {
        await this.$api.activate_user({username: this.user.username});
      }
    }
  }
}
</script>

<style scoped>

</style>