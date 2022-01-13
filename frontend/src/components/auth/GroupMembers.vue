<template>
  <div class="card" v-if="group?.id">
    <div class="card-header">
      {{ group?.name }}
    </div>
    <div class="card-body">
      <Placeholder :loading="loading" :big="true">
        <template v-slot:content>
          <ModalDialog :modal-buttons="modalButtons" :toggle-button="toggleButton"
                       :modal-title="`Select users to be added to group: ${group.name}`">
            <template v-slot:content>
              <ul class="list-group">
                <li v-for="user of users" :key="user.username" class="list-group-item">
                  <div class="form-check">
                  <input type="checkbox" :value="user.id" class="form-check-input"
                         :id="`add-user-id-${user.id}`" name="add-users"/>
                  <label class="form-check-label" :for="`add-user-id-${user.id}`">
                    {{ user.username }}
                  </label>
                  </div>
                </li>
              </ul>
            </template>
          </ModalDialog>
          <div class="table-responsive">
            <table class="table table-striped">
              <thead>
              <tr>
                <th></th>
                <th>Username</th>
                <th>Email</th>
                <th>Actions</th>
              </tr>
              </thead>
              <tbody>
              <template v-if="members.length > 0">
                <tr v-for="member of members" :key="member.id">
                  <td><input type="checkbox"/></td>
                  <td>{{ member.username }}</td>
                  <td>{{ member.email }}</td>
                  <td>TODO: Actions!</td>
                </tr>
              </template>
              <tr v-else>
                <td colspan="4">
                  <div class="alert alert-info">No members, yet.</div>
                </td>
              </tr>
              </tbody>
            </table>
          </div>
        </template>
      </Placeholder>
    </div>

  </div>
</template>

<script>
import {Button, ModalButton} from "@/composables/modals";
import Placeholder from "@/components/layout/Placeholder";
import ModalDialog from "@/components/layout/ModalDialog";

export default {
  name: "GroupMembers",
  components: {Placeholder, ModalDialog},
  props: {
    group: {
      required: true,
      type: Object
    },
    users: {
      required: true,
      type: Object
    }
  },
  data() {
    return {
      loading: true,
      members: [],
      toggleButton: new Button({
        css: "btn-outline-primary",
        icon: "person_add",
        text: "Add member"
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
    async addMembers() {
      const boxes = document.getElementsByName("add-users");
      const addUsers = Array.from(boxes)
          .filter(x => x.checked)
          .map(x => x.value)
          .map(x => this.users[x]);
      console.warn("TODO: Implement adding of users to group", addUsers);
      this.$alerts.push("warning", "Adding users to group is not implemented yet!");
    },
    async getMembers() {
      this.loading = true;
      if (!this.group) {
        this.loading = false;
        return []
      }
      this.members = await this.$api.getMembers({groupId: this.group.id});
      this.loading = false;
    }
  }
}
</script>

<style scoped>

</style>