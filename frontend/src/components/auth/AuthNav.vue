<template>
  <li class="nav-item" data-bs-toggle="tooltip" title="User Management">
    <router-link :to="{name: 'auth-manager'}" class="nav-link text-nowrap">
      <i class="eos-icons me-1">groups</i>
      User Mgmt.
    </router-link>
  </li>
  <li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle" href="#" id="nav-auth-dropdown" role="button"
       data-bs-toggle="dropdown" aria-expanded="false">
      <i class='eos-icons me-1'>{{ loggedInAs ? 'account_circle' : 'login' }}</i>
      Account
    </a>
    <div class="dropdown-menu" aria-labelledby="nav-auth-dropdown">
      <template v-if="loggedInAs">
        <p class="px-3">
          <i class='eos-icons me-1'>account_circle</i>
          Logged in as: <b>{{ loggedInAs }}</b>
        </p>
        <small class="px-3 text-muted">
          Session expires at: <b>{{ expires }}</b>.
        </small>
        <div class="dropdown-divider"/>
        <button class="dropdown-item" @click="this.$api.logout">
          <i class='eos-icons me-1'>logout</i>
          <span>Log out</span>
        </button>
      </template>
      <div v-else class="d-flex flex-column px-2 gap-2">
        <div class="form-floating">
          <input type="text" class="form-control" id="login-username" placeholder="Username"
                 v-model="username">
          <label for="login-username">Username</label>
        </div>
        <div class="form-floating">
          <input type="password" class="form-control" id="login-password"
                 placeholder="Password" v-model="password">
          <label for="login-password">Password</label>
        </div>
        <div class="d-flex">
          <button type="button" class="btn btn-primary flex-grow-1" @click="logIn()">
            <i class="eos-icons me-1">login</i>
            Login
          </button>
        </div>
      </div>
    </div>
  </li>
</template>

<script>
export default {
  name: "AuthNav",
  data() {
    return {
      username: '',
      password: ''
    }
  },
  created() {
    this.formatter = new Intl.DateTimeFormat(
          navigator.language,
          {dateStyle: "short", timeStyle: "short"}
      )
  },
  computed: {
    loggedInAs() {
      return this.$api.loggedIn;
    },
    expires() {
      const e = this.$api.expires;
      return e? this.formatter.format(e): "";
    }
  },
  methods: {
    logIn() {
      this.$api.login({username: this.username, password: this.password});
    }
  }
}
</script>

<style scoped>
.dropdown-menu {
  min-width: 20rem;
}
</style>