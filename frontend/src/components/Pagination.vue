<template>
<nav>
  <ul class="pagination">
    <li class="page-item">
      <a class="page-link" v-on:click="tryGoPrevious">
        <span>&laquo;</span>
      </a>
    </li>
    <li
      v-for="page in this.pages"
      :key="page"
      :class="{
        'page-item': this.totalEntities,
        active: page == this.currentPage,
      }"
    >
      <a class="page-link" v-on:click="$emit('goTo', page)">{{ page }}</a>
    </li>
    <li class="page-item">
      <a class="page-link" v-on:click="tryGoNext">
        <span>&raquo;</span>
      </a>
    </li>
  </ul>
</nav>
</template>

<script>
export default {
  name: "Pagination",
  props: ["totalEntities", "entitiesPerPage", "currentPage"],
  emits: ["goTo"],
  computed: {
      pages() {
          return Math.ceil(this.totalEntities / this.entitiesPerPage);
      }
  },
  methods: {
      tryGoPrevious(){
          if (this.currentPage > 1)
          this.$emit('goTo', this.currentPage - 1);
      },
      tryGoNext(){
          if (this.currentPage < this.pages)
          this.$emit('goTo', this.currentPage + 1);
      }
  }
};
</script>
