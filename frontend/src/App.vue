<template>
  <div>
    <nav class="navbar bg-navbar navbar-dark shadow">
      <div class="container-fluid">
        <router-link class="navbar-brand" to="/">SUSE <i>aimaas</i></router-link>

      </div>
    </nav>
    <div class="container-fluid mt-2">
      <router-view v-slot="{ Component }">
        <keep-alive include="EntityList">
          <component :is="Component"/>
        </keep-alive>
      </router-view>
    </div>
  </div>

</template>

<script>
import "bootstrap";
import "suse-bootstrap5-theme/dist/css/suse.css";

export default {
  name: 'App',
  components: {

  }
}
</script>