<template>
  <li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle text-nowrap" href="#" id="nav-help-dropdown" role="button"
       data-bs-toggle="dropdown" aria-expanded="false">
      <i class='eos-icons me-1'>help</i>
      Help
    </a>
    <div class="dropdown-menu" aria-labelledby="nav-help-dropdown">
      <a class="dropdown-item" href="/api/docs">
        <i class="eos-icons me-1">api</i>
        API Specification
      </a>
      <router-link :to="{name: 'help-about'}" class="dropdown-item">
        <i class="eos-icons me-1">help</i>
        About
      </router-link>
      <div class="dropdown-divider"></div>
      <div class="d-flex justify-content-between text-center">
        <a :href="`mailto:${apiInfo?.help.email}`" v-if="apiInfo?.help.email"
           title="Write your admins" class="dropdown-item">
          <i class="eos-icons me-1">email</i>
        </a>
        <a :href="apiInfo?.help.chat_url" v-if="apiInfo?.help.chat_url"
           title="Chat with your admins" class="dropdown-item">
          <i class="eos-icons me-1">chat</i>
        </a>
      </div>
      <div class="dropdown-divider"></div>
      <div class="dropdown-item d-flex justify-content-between">
        <span>Backend version:</span>
        <span class="ms-2">{{ apiInfo?.version }}</span>
      </div>
      <div class="dropdown-item d-flex justify-content-between">
        <span>Front version:</span>
        <span class="ms-2">{{ frontendVersion }}</span>
      </div>
    </div>
  </li>
</template>

<script>
export default {
  name: "HelpNav",
  inject: ["apiInfo"],
  data() {
    return {
      frontendVersion: "0.1.2"
    };
  }
}
</script>

<style scoped>

</style>
