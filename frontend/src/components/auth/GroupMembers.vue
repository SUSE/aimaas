<template>
  <div v-if="group" class="d-flex flex-row gap-2">
    <ModalDialog
      :modal-buttons="modalButtons"
      :toggle-button="toggleButton"
      :modal-title="`Select users to be added to group: ${group.name}`"
    >
      <template v-slot:content>
        <div class="list-group">
          <div
            v-for="user of users"
            :key="user.username"
            class="list-group-item"
          >
            <div class="form-check">
              <input
                type="checkbox"
                :value="user.id"
                class="form-check-input"
                :id="`add-user-id-${user.id}`"
                name="add-users"
              />
              <label class="form-check-label" :for="`add-user-id-${user.id}`">
                {{ user.username }}
              </label>
            </div>
          </div>
        </div>
      </template>
    </ModalDialog>
    <ConfirmButton
      :callback="removeMembers"
      btn-class="btn-outline-danger"
      v-if="selected.length > 0"
    >
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
                <input
                  type="checkbox"
                  :value="member.id"
                  class="form-check-input"
                  :id="`select-user-id-${member.id}`"
                  name="select-users"
                  @change="onSelect"
                />
              </div>
            </td>
            <td>
              <label
                class="form-check-label"
                :for="`select-user-id-${member.id}`"
              >
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

<script setup>
import { ref } from "vue";
import { Button, ModalButton } from "@/composables/modals";
import ModalDialog from "@/components/layout/ModalDialog.vue";
import ConfirmButton from "@/components/inputs/ConfirmButton.vue";
import { useAuthStore } from "@/store/auth";
import { api } from "@/composables/api";

const props = defineProps({
  group: {
    required: false,
    type: Object,
  },
});

const { users, loadUserData } = useAuthStore();

const selected = ref([]);
const toggleButton = new Button({
  css: "btn-outline-primary",
  icon: "person_add",
  text: "Add members",
});
const modalButtons = [
  new ModalButton({
    css: "btn-primary",
    icon: "person_add",
    text: "Add",
    callback: addMembers,
  }),
];

async function onSelect() {
  const elems = document.getElementsByName("select-users");
  selected.value = Array.prototype.filter
    .call(elems, (e) => e.checked)
    .map((e) => e.value);
}

const members = ref([]);

async function getMembers() {
  if (!props.group) {
    return
  }
  members.value = await api.getMembers({ groupId: props.group.id });
  selected.value = [];
}

async function addMembers() {
  const boxes = document.getElementsByName("add-users");
  const addUserIds = Array.from(boxes)
    .filter((input) => input.checked)
    .map((input) => input.value);
  const response = await api.addMembers({
    groupId: props.group.id,
    userIds: addUserIds,
  });
  if (response === true) {
    await getMembers();
  }
}

async function removeMembers() {
  const params = {
    groupId: props.group.id,
    userIds: selected.value,
  };
  const response = await api.removeMembers(params);
  if (response === true) {
    await getMembers();
  }
}

await Promise.all([ loadUserData(), getMembers() ])
</script>
