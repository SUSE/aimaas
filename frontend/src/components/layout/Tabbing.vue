<template>
  <div>
    <ul class="nav nav-tabs" id="schemaTabs" role="tablist">
      <li v-for="(tab, idx) in tabs" data-bs-toggle="tooltip" :key="tab.name" :title="tab.tooltip"
          class="nav-item">
        <button class="nav-link" :class="navLinkClass(idx)"
                type="button" v-on:click="currentTab = idx">
          <i class='eos-icons'>{{ tab.icon }}</i>
          {{ tab.name }}
        </button>
      </li>
    </ul>
    <div class="tab-content">
      <div class="tab-pane show active border p-2" role="tabpanel">
        <keep-alive>
          <component :is="tabs[currentTab].component" v-bind="bindArgs" v-on="tabEvents"/>
        </keep-alive>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "Tabbing",
  props: {
    tabs: {
      required: true,
      type: Array
    },
    initialTab: {
      required: false,
      type: Number,
      default: 0
    },
    bindArgs: {
      required: true,
      type: Object
    },
    tabEvents: {
      required: false,
      type: Object,
      default: function () {
        return {}
      }
    }
  },
  data() {
    return {
      currentTab: this.initialTab
    }
  },
  methods: {
    navLinkClass(tabIndex) {
      if (this.currentTab === tabIndex) {
        return "active";
      }
      else if (this.tabs[tabIndex]?.disabled) {
        return "disabled";
      }
      return "";
    }
  }
}
</script>

<style scoped>

</style>