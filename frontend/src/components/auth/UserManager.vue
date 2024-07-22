<template>
  <div class="d-flex gap-3 flex-wrap users-list">
    <div class="users-list">
      <ul class="list-group">
        <li class="list-group-item">
          <input type="text" name="username" v-model="usernameFilter" placeholder="Filter username"
                 class="form-control"/>
        </li>
        <li class="list-group-item" v-for="user in filteredUsers" :key="user.id">
          <button class="btn btn-link" @click="selectUser(user)">
            {{ user.username }}
          </button>

        </li>
        <li v-if="filteredUsers.length < 1" class="list-group-item p-0">
          <div class="alert alert-info m-0 text-center">No matching users.</div>
        </li>
      </ul>
    </div>
    <div v-show="selectedUser" class="user-detail flex-fill">
      <h4>{{ selectedUser?.username}}</h4>
      <Tabbing :bind-args="bindArgs" :tabs="tabs" />
    </div>
  </div>
</template>

<script>
import { markRaw } from "vue";
import UserDetails from "@/components/auth/UserDetails.vue";
import PermissionList from "@/components/auth/PermissionList.vue";
import Tabbing from "@/components/layout/Tabbing.vue";
import { useAuthStore } from "@/store/auth";

export default {
  name: "UserManager",
  components: { Tabbing },
  async setup() {
    const { users, loadUserData } = useAuthStore();
    await loadUserData();
    return { users }
  },
  data() {
    return {
      usernameFilter: "",
      selectedUser: null,
      tabs: [
        {
          name: "Details",
          component: markRaw(UserDetails),
          icon: "details",
          tooltip: "Show user details"
        },
        {
          name: "Permissions",
          component: markRaw(PermissionList),
          icon: "security",
          tooltip: "Manage user permissions"
        }
      ]
    }
  },
  methods: {
    selectUser(user) {
      if (this.selectedUser?.id === user.id) {
        this.selectedUser = null;
      } else {
        this.selectedUser = user
      }
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
      return [
        { user: this.selectedUser },
        { recipientType: "User", recipientId: this.selectedUser?.id },
      ]
    }
  }
}
</script>

<style lang="css" scoped>
.users-list {
  flex: 1;
  min-width: 220px;
}

.user-detail {
  flex: 2;
  min-width: 360px;
}
</style>
