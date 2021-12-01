<template>
<router-view v-slot="{ Component }">
    <keep-alive include="EntityList">
      <component :is="Component"/>
    </keep-alive>
  </router-view>
</template>

<script>
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap";

export default {
  name: 'App',
  components: {

  }
}
</script>