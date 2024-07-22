<template>
  <ul class="list-group">
    <li class="list-group-item" v-for="change in items" :key="change.id">
          <div class="row text-black p-2" :class="`bg-${CHANGE_STATUS_MAP[change.status]}`">
            <div class="col-md-1 d-flex flex-column align-self-center">
              <h4 class="p-0 m-0" data-bs-toggle="tooltip"
                  :title="`${change.change_type} ${change.object_type}`">
                <i class="eos-icons">{{ actionIcon(change.change_type) }}</i>
              </h4>
            </div>
            <div class="col-md-2 d-flex flex-column align-items-end">
              <small>Created at:</small>
              <span>{{ formatDate(change.created_at) }}</span>
            </div>
            <div class="col-md-2 d-flex flex-column align-items-end">
              <small>Created by:</small>
              <span>{{ change.created_by }}</span>
            </div>
            <template v-if="change.reviewed_at">
              <div class="col-md-2 d-flex flex-column align-items-end border-start border-dark">
                <small>Reviewed at:</small>
                <span>{{ formatDate(change.reviewed_at) }}</span>
              </div>
              <div class="col-md-2 d-flex flex-column align-items-end">
                <small>Reviewed by:</small>
                <span>{{ change.reviewed_by }}</span>
              </div>
              <div class="col-md-3 d-flex flex-column align-items-end">
                <small>Comment:</small>
                <small>{{ change.comment }}</small>
              </div>
            </template>
            <div v-else class="col-md-7 d-flex gap-3 p-0 m-0">
              <ConfirmWithComment :callback="onDecline" btn-class="btn-outline-danger shadow-sm"
                                  class="flex-grow-1" data-bs-toggle="tooltip" :vertical="true"
                                  title="Decline request and do not apply changes."
                                  :value="change.id"
                                  placeholder="Sorry, I have to decline.">
                <template v-slot:label>
                  <i class="eos-icons me-1">thumb_down</i>
                  Decline
                </template>
              </ConfirmWithComment>
              <ConfirmWithComment :callback="onApprove" btn-class="btn-success shadow-sm"
                             class="flex-grow-1" data-bs-toggle="tooltip" :vertical="true"
                             title="Accept request and apply changes to database."
                             :value="change.id" placeholder="Looks good to me.">
                <template v-slot:label>
                  <i class="eos-icons me-1">thumb_up</i>
                  Approve
                </template>
              </ConfirmWithComment>
            </div>
          </div>
          <ChangeDetails :changeId="change.id" :schema="additionalArgs?.schema"
                         :entitySlug="additionalArgs?.entitySlug"
                         :is-bound="additionalArgs?.isBound" :object-type="change.object_type"/>
        </li>
        <li v-if="items.length < 1" class="list-group-item">
          <div class="alert alert-info m-0">No changes to display.</div>
        </li>
  </ul>
</template>

<script>
import {formatDate, CHANGE_STATUS_MAP} from "@/utils";
import ConfirmWithComment from "@/components/inputs/ConfirmWithComment.vue";
import ChangeDetails from "@/components/change_review/ChangeDetails.vue";

export default {
  name: "ChangePage",
  components: {ChangeDetails, ConfirmWithComment},
  props: {
    items: {
      required: true,
      type: Array
    },
    additionalArgs: {
      required: false,
      type: Object
    }
  },
  inject: ["updatePendingRequests"],
  data() {
    return {
      changeDetails: {},
      CHANGE_STATUS_MAP
    }
  },
  methods: {
    formatDate,
    actionIcon(actionType) {
      return this.CHANGE_STATUS_MAP[actionType.toLowerCase()];
    },
    fakeReview(changeId, verdict) {
      for (let change of this.items) {
        if (changeId == change.id) {
          change.reviewed_at = Date.now();
          change.reviewed_by = 'me';
          change.status = `${verdict}D`;
        }
      }
    },
    async review(changeId, verdict, comment) {
      const result = await this.$api.reviewChanges({
        changeId: changeId,
        verdict: verdict,
        comment: comment
      });
      if (result) {
        this.fakeReview(changeId, verdict);
        this.updatePendingRequests();
      }
    },
    async onDecline(event, comment) {
      await this.review(event.target.value, 'DECLINE', comment);
    },
    async onApprove(event, comment) {
      await this.review(event.target.value, 'APPROVE', comment);
    }
  }
}
</script>

<style scoped>

</style>
