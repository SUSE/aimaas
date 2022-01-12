<template>
  <div v-if="group?.id">
    <Placeholder :loading="loading" :big="true">
      <template v-slot:content>
        <div class="d-flex flex-row gap-2">
          <ModalDialog :modal-buttons="modalButtons" :toggle-button="toggleButton"
                       :modal-title="`Select users to be added to group: ${group.name}`">
            <template v-slot:content>
              <div class="list-group">
                <div v-for="user of users" :key="user.username" class="list-group-item">
                  <div class="form-check">
                    <input type="checkbox" :value="user.id" class="form-check-input"
                           :id="`add-user-id-${user.id}`" name="add-users"/>
                    <label class="form-check-label" :for="`add-user-id-${user.id}`">
                      {{ user.username }}
                    </label>
                  </div>
                </div>
              </div>
            </template>
          </ModalDialog>
          <ConfirmButton :callback="removeMembers" btn-class="btn-outline-danger"
                         v-if="selected.length > 0">
            <template v-slot:label>
              <i class="eos-icons me-1">delete</i>
              Delete {{ selected.length }} member(s)
            </template>
          </ConfirmButton>
        </div>
        <div class="table-responsive">
          <table class="table table-striped">
            <thead>
            <tr>
              <th></th>
              <th>Username</th>
              <th>Email</th>
            </tr>
            </thead>
            <tbody>
            <template v-if="members.length > 0">
              <tr v-for="member of members" :key="member.id">
                <td>
                  <div class="form-check">
                    <input type="checkbox" :value="member.id" class="form-check-input"
                           :id="`select-user-id-${member.id}`" name="select-users"
                           @change="onSelect"/>
                  </div>
                </td>
                <td>
                  <label class="form-check-label" :for="`select-user-id-${member.id}`">
                    {{ member.username }}
                  </label>
                </td>
                <td>{{ member.email }}</td>
              </tr>
            </template>
            <tr v-else>
              <td colspan="4 p-0">
                <div class="alert alert-info m-0">No members, yet.</div>
              </td>
            </tr>
            </tbody>
          </table>
        </div>
      </template>
    </Placeholder>
  </div>
</template>

<script>
import {Button, ModalButton} from "@/composables/modals";
import Placeholder from "@/components/layout/Placeholder";
import ModalDialog from "@/components/layout/ModalDialog";
import ConfirmButton from "@/components/inputs/ConfirmButton";

export default {
  name: "GroupMembers",
  components: {Placeholder, ModalDialog, ConfirmButton},
  inject: ["groups", "users"],
  props: {
    group: {
      required: true,
      type: Object
    }
  },
  data() {
    return {
      loading: true,
      members: [],
      selected: [],
      toggleButton: new Button({
        css: "btn-outline-primary",
        icon: "person_add",
        text: "Add members"
      }),
      modalButtons: [
        new ModalButton({
          css: "btn-primary",
          icon: "person_add",
          text: "Add",
          callback: this.addMembers
        })
      ]
    }
  },
  watch: {
    async group() {
      await this.getMembers();
    }
  },
  async mounted() {
    await this.getMembers();
  },
  methods: {
    async onSelect() {
      const elems = document.getElementsByName("select-users");
      this.selected = Array.prototype.filter.call(elems, e => e.checked).map(e => e.value);
    },
    async addMembers() {
      const boxes = document.getElementsByName("add-users");
      const addUserIds = Array.from(boxes)
          .filter(x => x.checked)
          .map(x => x.value);
      const response = this.$api.addMembers({groupId: this.group.id, userIds: addUserIds});
      if (response === true) {
        await this.getMembers();
      }
    },
    async getMembers() {
      this.loading = true;
      if (!this.group) {
        this.loading = false;
        this.members = [];
        return;
      }
      this.members = await this.$api.getMembers({groupId: this.group.id});
      this.selected = [];
      this.loading = false;
    },
    async removeMembers() {
      const params = {
        groupId: this.group.id,
        userIds: this.selected
      };
      const response = await this.$api.removeMembers(params);
      if (response === true) {
        await this.getMembers();
      }
    }
  }
}
</script>

<style scoped>

</style>