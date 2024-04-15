<template>
  <div class="d-md-flex flex-row gap-2 align-items-start">
    <ModalDialog
      :modal-buttons="modalButtons"
      :toggle-button="toggleButton"
      modal-title="Grant permission"
    >
      <template v-slot:content>
        <SelectInput
          label="Permission"
          :args="{ id: 'permission' }"
          :options="availablePermissions"
          :required="true"
          v-model="newPermData.permission"
        />
        <SelectInput
          label="Recipient Type"
          v-model="newPermData.recipientType"
          :args="{ id: 'recipient_type', disabled: recipientType !== null }"
          :options="recipientOptions"
          :required="recipientType === null"
          @change="newPermData.recipientName = null"
        />
        <DropdownSelect
          label="Recipient Name"
          v-model="newPermData.recipientName"
          :args="{ id: 'recipient_name' }"
          :disabled="recipientType !== null"
          :required="recipientType === null"
          :options="recipientNameOptions"
        />
        <SelectInput
          label="Object Type"
          v-model="newPermData.objType"
          :args="{
            id: 'obj_type',
            disabled:
              objectType !== null ||
              ['SU', 'SCH_C', 'SCH_D'].includes(newPermData.permission),
          }"
          :required="
            objectType === null &&
            !['SU', 'SCH_C'].includes(newPermData.permission)
          "
          :options="objectTypeOptions"
        />
        <IntegerInput
          label="Entity ID"
          v-model="newPermData.objId"
          :args="{ id: 'obj_id', disabled: objectType === 'Entity' }"
          :required="newPermData.objType === 'Entity'"
          v-if="newPermData.objType === 'Entity'"
        />
        <DropdownSelect
          label="Object ID"
          v-model="newPermData.objId"
          v-else
          :args="{ id: 'obj_id' }"
          :disabled="objectType !== null"
          :required="objectType === null"
          :options="objectIdOptions"
        />
      </template>
    </ModalDialog>
    <ConfirmButton
      btnClass="btn-outline-danger"
      :callback="onDelete"
      :vertical="true"
      v-if="selected.length > 0"
    >
      <template v-slot:label>
        <i class="eos-icons me-1">delete</i>
        Revoke {{ selected.length }} permission(s)
      </template>
    </ConfirmButton>
  </div>
  <div class="table-responsive">
    <table class="table table-striped">
      <thead>
        <tr>
          <th></th>
          <th>Permission</th>
          <th>{{ secondColumnName }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="perm in permissions" :key="perm.id">
          <td>
            <input
              type="checkbox"
              class="form-check-input"
              name="PermissionSelect"
              :id="`perm-${perm.id}`"
              :value="perm.id"
              @click="onSelect"
              v-if="!isPermissionInherited(perm)"
            />
            <i
              v-else
              class="eos-icons me-1"
              data-bs-toggle="tooltip"
              title="Permission is inherited"
            >
              lock
            </i>
          </td>
          <td>{{ getObjectPermission(perm) }}</td>
          <td>
            <template v-if="objectType">
              <i class="eos-icons me-1">{{
                recipientIcons[perm.recipient_type]
              }}</i>
              {{ perm.recipient_name }}
            </template>
            <template v-else>
              <i class="eos-icons me-1">{{ objectIcons[perm.obj_type] }}</i>
              {{ getObjectName(perm) }}
            </template>
          </td>
        </tr>
        <tr v-if="permissions.length < 1">
          <td colspan="3" class="p-0">
            <div class="alert alert-info text-center m-0">
              No permissions granted, yet.
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, computed, inject, defineProps } from "vue";
import ConfirmButton from "@/components/inputs/ConfirmButton";
import ModalDialog from "@/components/layout/ModalDialog";
import SelectInput from "@/components/inputs/SelectInput";
import DropdownSelect from "@/components/inputs/DropdownSelect";
import IntegerInput from "@/components/inputs/IntegerInput";
import { Button, ModalButton } from "@/composables/modals";
import { useAuthStore } from "@/store/auth";
import { api } from "@/composables/api";

const availableSchemas = inject("availableSchemas");
const props = defineProps({
  recipientType: {
    type: String,
    required: false,
    default: null,
    validator(value) {
      return ["Group", "User"].includes(value);
    },
  },
  recipientId: {
    type: Number,
    required: false,
    default: null,
  },
  objectType: {
    type: String,
    required: false,
    default: null,
    validator(value) {
      return ["Group", "Entity", "Schema"].includes(value);
    },
  },
  objectId: {
    type: Number,
    required: false,
    default: null,
  },
});

const { users, groups, loadGroupData, loadUserData } = useAuthStore();

const availableGroups = groups;
const availableUsers = ref(users);
const selected = ref([]);

const recipientIcons = {
  Group: "group",
  User: "person",
};

const objectIcons = {
  Schema: "namespace",
  Entity: "table_rows",
  Group: "group",
};

const toggleButton = new Button({
  icon: "add",
  text: "Grant new permission",
  css: "btn-outline-primary",
});

const modalButtons = [
  new ModalButton({
    callback: onAddition,
    icon: "add",
    text: "Grant",
    css: "btn-primary",
  }),
];

const permOptions = [
  {
    value: "SU",
    text: "Superuser",
  },
  {
    value: "UM",
    text: "User Management",
  },
  {
    value: "SCH_C",
    text: "Schema: Create",
  },
  {
    value: "SCH_U",
    text: "Schema: Update",
  },
  {
    value: "SCH_D",
    text: "Schema: Delete",
  },
  {
    value: "SCH_R",
    text: "Schema: Read",
  },
  {
    value: "ENT_C",
    text: "Entity: Create",
  },
  {
    value: "ENT_U",
    text: "Entity: Update",
  },
  {
    value: "ENT_D",
    text: "Entity: Delete",
  },
  {
    value: "ENT_R",
    text: "Entity: Read",
  },
];
const recipientOptions = [
  {
    value: "Group",
  },
  {
    value: "User",
  },
];

const permissions = ref([]);
if (props.objectId || props.objectType || props.recipientId | props.recipientType) {
  permissions.value = await api.getPermissions({
    recipientType: props.recipientType,
    recipientId: props.recipientId,
    objType: props.objectType,
    objId: props.objectId,
  });
}

const availablePermissions = computed(() => {
  if (props.objectType === "Group") {
    return permOptions.filter((x) => x.value === "UM");
  }
  if (props.objectType === "Schema") {
    return permOptions.filter((x) => /^SCH_[UR]|ENT_[CRUD]/.test(x.value));
  }
  if (props.objectType === "Entity") {
    return permOptions.filter((x) => /^ENT_[UR]/.test(x.value));
  }
  return permOptions;
});

const secondColumnName = computed(() => {
  if (props.recipientId) {
    return "Object";
  }
  if (props.objectType) {
    return "Who";
  }
  return "?";
});

const recipientName = computed(() => {
  if (props.recipientType === "Group") {
    return availableGroups.value[props.recipientId]?.name;
  }
  return availableUsers.value[props.recipientId]?.username;
});

const newPermData = ref({
  permission: null,
  recipientType: props.recipientType,
  recipientName: recipientName.value,
  objType: props.objectType,
  objId: props.objectId,
});

const recipientNameOptions = computed(() => {
  if (newPermData.value.recipientType == "Group") {
    return Object.values(availableGroups.value).map((x) => ({ value: x.name }));
  }

  if (newPermData.value.recipientType == "User") {
    return Object.values(availableUsers.value).map((x) => ({
      value: x.username,
    }));
  }

  return [];
});

const objectTypeOptions = computed(() => {
  const nochoice = { value: null, text: "(none)" };
  if (newPermData.value.permission === "SU") {
    return [nochoice];
  }
  if (newPermData.value.permission === "UM") {
    return [nochoice, { value: "Group" }];
  }
  if (/^SCH_[UR]/.test(newPermData.value.permission)) {
    return [{ value: "Schema" }];
  }
  if (/^ENT_[CD]/.test(newPermData.value.permission)) {
    return [{ value: "Schema" }];
  }
  if (/^ENT_[UR]/.test(newPermData.value.permission)) {
    return [{ value: "Entity" }, { value: "Schema" }];
  }
  return [
    nochoice,
    { value: "Group" },
    { value: "Entity" },
    { value: "Schema" },
  ];
});

const objectIdOptions = computed(() => {
  if (newPermData.value.objType === "Group") {
    return Object.values(availableGroups.value).map((x) => {
      return { value: x.id, text: x.name };
    });
  }
  if (newPermData.value.objType === "Schema") {
    return availableSchemas.value.map((x) => {
      return { value: x.id, text: x.name };
    });
  }
  return [];
});

function isPermissionInherited(perm) {
  if (
    props.recipientType &&
    props.recipientType === perm.recipient_type &&
    recipientName.value === perm.recipient_name
  ) {
    return false;
  }
  if (
    props.objectType &&
    props.objectType === perm.obj_type &&
    props.objectId === perm.obj_id
  ) {
    return false;
  }
  return true;
}

const loading = ref(false);
async function load() {
  loading.value = true;
  if (
    (props.recipientType && props.recipientId) ||
    (props.objectType && props.objectId)
  ) {
    permissions.value = await api.getPermissions({
      recipientType: props.recipientType,
      recipientId: props.recipientId,
      objType: props.objectType,
      objId: props.objectId,
    });
  } else {
    permissions.value = [];
  }
  selected.value = [];
  loading.value = false;
}

function getObjectName(perm) {
  if (perm.obj_type === "Group") {
    // Deleting a group doesn't cascade delete related permissions
    // -> hence the group no longer exists, but the permissions do.
    if (availableGroups.value[perm.obj_id]) {
      return availableGroups.value[perm.obj_id].name;
    }

    return "N/A";
  }

  if (perm.obj_type === "User") {
    return availableGroups.value[perm.obj_id].username;
  }

  if (perm.obj_type === "Schema") {
    return availableSchemas.value
      .filter((x) => x.id === perm.obj_id)
      .map((x) => x.name)[0];
  }
  return perm.obj_id;
}

function getObjectPermission(perm) {
  return permOptions
    .filter((x) => x.value === perm.permission)
    .map((x) => x.text)[0];
}

function onSelect() {
  const elems = document.getElementsByName("PermissionSelect");
  selected.value = Array.prototype.filter
    .call(elems, (e) => e.checked)
    .map((e) => e.value);
}

async function onDelete() {
  await api.revokePermissions({
    permissionIds: selected.value.map((x) => parseInt(x)),
  });
  await load();
}

async function onAddition() {
  await api.grantPermission(newPermData.value);
  await load();
}

await Promise.all([loadGroupData(), loadUserData()]);
</script>
