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
          <Suspense timeout="0">
            <component v-if="currentTab !== undefined" :is="tabs[currentTab].component" v-bind="bindArgs[currentTab] ?? {}" v-on="tabEvents" :key="currentTab"/>
            <template #fallback>
              <Placeholder :big="true" />
            </template>
          </Suspense>
      </div>
    </div>
  </div>
</template>

<script>
import Placeholder from "@/components/layout/Placeholder.vue";

export default {
  name: "Tabbing",
  components: { Placeholder },
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
      required: false,
      type: Array,
      default: function () {
        return [];
      },
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
  },
  watch: {
    async bindArgs() {
      // force-recreate the tab content component if its props (bind args) change reactively
      // (which also triggers the suspense)
      const tabIdx = this.currentTab;
      this.currentTab = undefined;
      setTimeout(() => this.currentTab = tabIdx, 0);
    }
  }
}
</script>
