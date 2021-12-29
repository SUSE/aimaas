<template>
  <li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle" href="#" id="nav-auth-dropdown" role="button"
       data-bs-toggle="dropdown" aria-expanded="false">
      <i class='eos-icons me-1'>{{ loggedInAs ? 'account_circle' : 'login' }}</i>
      Account
    </a>
    <ul class="dropdown-menu" aria-labelledby="nav-auth-dropdown">
      <template v-if="loggedInAs">
        <li>
          <div class="dropdown-header">
            <i class='eos-icons me-1'>account_circle</i>
            Logged in as: <b>{{ loggedInAs }}</b>
          </div>
        </li>
        <li>
          <hr class="dropdown-divider">
        </li>
        <li>
          <div class="dropdown-item">
            <i class='eos-icons me-1'>logout</i>
            <span>Log out</span>
          </div>
        </li>
      </template>
      <template v-else>
        <li>
          <div class="dropdown-item d-grid gap-2">
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
        </li>
      </template>
    </ul>
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
  computed: {
    loggedInAs() {
      return this.$api.loggedIn;
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