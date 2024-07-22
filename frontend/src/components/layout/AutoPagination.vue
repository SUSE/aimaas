<template>
  <Pagination :total-items="total" v-model="page" ref="pagination" @change="loadPage()">
    <template v-slot:default>
      <Placeholder :loading="loading" :big="true">
        <template v-slot:content>
          <component :is="theComponent" :items="items" :additional-args="argsForBinding"/>
        </template>
      </Placeholder>
    </template>
  </Pagination>
</template>

<script>
import Pagination from "@/components/layout/Pagination.vue";
import Placeholder from "@/components/layout/Placeholder.vue";

export default {
  name: "AutoPagination",
  components: {Pagination, Placeholder},
  props: {
    getFunc: {
      type: Function,
      required: true
    },
    theComponent: {
      required: true
    },
    argsForBinding: {
      required: false,
      type: Object
    }
  },
  data() {
    return {
      page: 1,
      total: 0,
      items: [],
      loading: true
    }
  },
  computed: {
    pageSize() {
      return this.$refs.pagination?.pageSize || 10;
    }
  },
  methods: {
    async loadPage() {
      this.loading = true;
      const response = await this.getFunc({page: this.page, size: this.pageSize});
      this.total = response.total;
      this.items = response.items;
      this.loading = false;
    }
  },
  watch: {
    async page() {
      await this.loadPage();
    }
  },
  async mounted() {
    await this.loadPage();
  }
}
</script>

<style scoped>

</style>
