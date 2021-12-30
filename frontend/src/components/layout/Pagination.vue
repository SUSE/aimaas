<template>
  <div class="my-1">
    <nav>
      <ul class="pagination mb-0">
        <li class="page-item">
          <a class="page-link" v-on:click="tryGoPrevious">
            <span>&laquo;</span>
          </a>
        </li>
        <li v-for="page in this.pages" :key="page"
            :class="{'page-item': this.totalItems, active: page === this.currentPage}">
          <a class="page-link" v-on:click="$emit('goTo', page)">{{ page }}</a>
        </li>
        <li class="page-item">
          <a class="page-link" v-on:click="tryGoNext">
            <span>&raquo;</span>
          </a>
        </li>
      </ul>
    </nav>
  </div>
</template>

<script>
export default {
  name: "Pagination",
  props: {
    totalItems: {
      type: Number,
      required: true
    },
    itemsPerPage: {
      type: Number,
      required: true
    },
    currentPage: {
      type: Number,
      default: 1
    }
  },
  emits: ["goTo"],
  computed: {
    pages() {
      return Math.ceil(this.totalItems / this.itemsPerPage);
    }
  },
  methods: {
    tryGoPrevious() {
      if (this.currentPage > 1)
        this.$emit('goTo', this.currentPage - 1);
    },
    tryGoNext() {
      if (this.currentPage < this.pages)
        this.$emit('goTo', this.currentPage + 1);
    }
  }
};
</script>
