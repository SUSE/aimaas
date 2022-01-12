<template>
  <div class="row m-0">
    <div class="col-md-3">
      <ul class="list-group">
        <li class="list-group-item">
          <input type="text" name="username" v-model="usernameFilter" placeholder="Filter username"
                 class="form-control"/>
        </li>
        <li class="list-group-item" v-for="user in filteredUsers" :key="user.id">
          <button class="btn btn-link" @click="selectedUser = user">
            {{ user.username }}
          </button>

        </li>
        <li v-if="filteredUsers.length < 1" class="list-group-item p-0">
          <div class="alert alert-info m-0 text-center">No matching users.</div>
        </li>
      </ul>
    </div>
    <div class="col-md-9">
      <h4 class="ps-5">{{ selectedUser?.username}}</h4>
      <Tabbing v-show="selectedUser" :bind-args="bindArgs" :tabs="tabs" ref="userTab"/>
    </div>
  </div>
</template>

<script>
import UserDetails from "@/components/auth/UserDetails";
import PermissionList from "@/components/auth/PermissionList";
import Tabbing from "@/components/layout/Tabbing";

export default {
  name: "UserManager",
  inject: ["users"],
  components: {Tabbing},
  data() {
    return {
      usernameFilter: "",
      selectedUser: null,
      tabs: [
        {
          name: "Details",
          component: UserDetails,
          icon: "details",
          tooltip: "Show user details"
        },
        {
          name: "Permissions",
          component: PermissionList,
          icon: "security",
          tooltip: "Manage user permissions"
        }
      ]
    }
  },
  computed: {
    filteredUsers() {
      if (this.usernameFilter.length > 0) {
        return Object.values(this.users).filter(x => x.username.includes(this.usernameFilter));
      }
      return Object.values(this.users);
    },
    bindArgs() {
      const activeTab = this.$refs.userTab?.currentTab || 0;
      if (activeTab === 1) {
        return {recipientType: "User", recipientId: this.selectedUser.id};
      }
      return {user: this.selectedUser};
    }
  }
}
</script>

<style scoped>

</style>