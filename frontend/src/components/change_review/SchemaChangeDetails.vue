<template>
  <template v-if="changeId in changeDetails">
    <template v-if="changeDetails[changeId].length > 0">
      <table class="table">
        <thead>
        <tr>
          <th v-for="heading in tableHeadings" :key="heading">
            {{ heading }}
          </th>
        </tr>
        </thead>
        <tbody>
        <tr v-for="(change, idx) in changeDetails[changeId]" :key="`${changeId}/${idx}`">
          <td v-for="heading in tableHeadings" :key="`${changeId}/${idx}/${heading}`">
            <template v-if="heading === 'action'">
              <i class="eos-icons" data-bs-toggle="tooltip" :title="change[heading]">
                {{ CHANGE_STATUS_MAP[change[heading]] }}
              </i>
            </template>
            <template v-else-if="typeof change[heading] === 'boolean'">
              <i class="eos-icons" :class="change[heading] ? 'text-success' : 'text-danger'"
                 data-bs-toggle="tooltip" :title="change[heading]">
                {{ change[heading] ? 'thumb_up' : 'thumb_down' }}
              </i>
            </template>
            <template v-else>
              {{ change[heading] }}
            </template>
          </td>
        </tr>
        </tbody>
      </table>
    </template>
    <div v-else class="alert alert-info">No additional details.</div>
  </template>
  <button v-else type="button" class="btn btn-link" @click="loadDetails()">
    Load details
  </button>
</template>

<script>
import {CHANGE_STATUS_MAP} from "@/utils";
import {loadChangeDetails, sortChangeHeaders} from "@/composables/changes";

export default {
  name: "SchemaChangeDetails",
  props: {
    changeId: {
      required: true,
      type: Number
    },
    schema: {
      required: true,
      type: Object
    },
    entitySlug: {
      required: false,
      type: String,
      default: null
    }
  },
  data() {
    return {
      CHANGE_STATUS_MAP,
      changeDetails: {}
    }
  },
  computed: {
    tableHeadings() {
      const keys = [];
      for (const c of this.changeDetails[this.changeId]) {
        for (const k of Object.keys(c)) {
          if (!keys.includes(k)) {
            keys.push(k);
          }
        }
      }
      keys.sort(sortChangeHeaders);
      return keys;
    }
  },
  methods: {
    async transformDetails(details) {
      const transformed = [];
      for (const action of ['add', 'delete', 'update']) {
        for (let change of details.changes[action]) {
          change.action = action;
          transformed.push(change);
        }
      }
      return transformed;
    },
    async loadDetails() {
      return loadChangeDetails(this.$api, this.schema.slug, this.entitySlug, this.changeId,
          this.changeDetails, this.transformDetails);
    }
  }
}
</script>

<style scoped>

</style>