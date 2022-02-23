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
      frontendVersion: "0.1.0rc1"
    };
  }
}
</script>

<style scoped>

</style>