<template>
  <div class="container w-50 position-absolute top-0 end-0 m-3" id="alert-contaier">
    <div v-for="alert of alerts" :key="alert.id"
         class="alert shadow alert-dismissible fade show" :class="`alert-${alert.level}`"
         role="alert">
      <i class="eos-icons me-1">{{ icons[alert.level] }}</i>
      {{ alert.message }}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
  </div>
</template>

<script>

export default {
  name: "AlertDisplay",
  data() {
    return {
      alerts: {},
      icons: {
        primary: 'notification_important',
        secondary: 'notifications',
        success: 'verified',
        danger: 'error',
        warning: 'warning',
        info: 'info',
        light: 'notifications',
        dark: 'notifications',
        cta: 'new-releases'
      }
    }
  },
  methods: {
    getAlerts() {
      for (let alert of this.$alerts.values) {
        if (alert.id in this.alerts) {
          continue;
        }
        this.alerts[alert.id] = alert;
        setTimeout(this.hideAlert, 3000, alert.id);
        this.$alerts.pop(alert.id);
      }
    },
    hideAlert(alertId) {
      try {
        delete this.alerts[alertId];
      } catch (e) {
        console.debug("Alert", alertId, "already removed?");
      }
    }
  },
  mounted() {
    this.getAlerts();
    setInterval(this.getAlerts, 300);
  },
}
</script>

<style scoped>
#alert-contaier {
  z-index: 10;
}
</style>