<template>
  <li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle" href="#" id="nav-help-dropdown" role="button"
       data-bs-toggle="dropdown" aria-expanded="false">
      <i class='eos-icons me-1'>help</i>
      Help
    </a>
    <div class="dropdown-menu" aria-labelledby="nav-help-dropdown">
      <div class="dropdown-divider"></div>
      <div class="dropdown-item d-flex justify-content-between">
        <span>Backend version:</span>
        <span class="ms-2">{{ backendVersion }}</span>
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
  data() {
    return {
      backendVersion: null,
      frontendVersion: "0.1.0rc1"
    };
  },
  async created() {
    await this.load();
  },
  methods: {
    async load() {
      const response = await this.$api.getInfo();
      this.backendVersion = response.version;
    }
  }
}
</script>

<style scoped>

</style>