<template>
  <Placeholder :loading="loading">
    <template v-slot:content>
      <div class="d-md-flex flex-row gap-2 align-items-start">
        <ModalDialog :modal-buttons="modalButtons" :toggle-button="toggleButton"
                     modal-title="Grant permission">
          <template v-slot:content>
            <SelectInput label="Permission" :args="{id: 'permission'}"
                         :options="availablePermissions"
                         :required="true" v-model="newPermData.permission"/>
            <SelectInput label="Recipient Type" v-model="newPermData.recipientType"
                         :args="{id: 'recipient_type', disabled: recipientType !== null}"
                         :options="recipientOptions" :required="recipientType === null"
                         @change="updateRecipientNameOptions(); newPermData.recipientName = null"/>
            <DropdownSelect label="Recipient Name" v-model="newPermData.recipientName"
                            :args="{id: 'recipient_name'}" :disabled="recipientType !== null"
                            :required="recipientType === null" :options="recipientNameOptions"/>
            <SelectInput label="Object Type" v-model="newPermData.objType"
                         :args="{id: 'obj_type', disabled: objectType !== null || ['SU', 'SCH_C', 'SCH_D'].includes(newPermData.permission)}"
                         :required="objectType === null && !['SU', 'SCH_C'].includes(newPermData.permission)"
                         :options="objectTypeOptions"/>
            {{ newPermData.objType }}
            <IntegerInput label="Entity ID" v-model="newPermData.objId"
                          :args="{id: 'obj_id', disabled: objectType === 'Entity'}"
                          :required="newPermData.objType === 'Entity'"
                          v-if="newPermData.objType === 'Entity'"/>
            <DropdownSelect label="Object ID" v-model="newPermData.objId" v-else
                            :args="{id: 'obj_id'}" :disabled="objectType !== null"
                            :required="objectType === null" :options="objectIdOptions"/>
          </template>
        </ModalDialog>
        <ConfirmButton btnClass="btn-outline-danger" :callback="onDelete" :vertical="true"
                       v-if="selected.length > 0">
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
              <input type="checkbox" class="form-check-input" name="PermissionSelect"
                     :id="`perm-${perm.id}`" :value="perm.id" @click="onSelect"
                     v-if="!isPermissionInherited(perm)"/>
              <i v-else class="eos-icons me-1" data-bs-toggle="tooltip"
                 title="Permission is inherited">
                lock
              </i>
            </td>
            <td>{{ getObjectPermission(perm) }}</td>
            <td>
              <template v-if="objectType">
                <i class="eos-icons me-1">{{ recipientIcons[perm.recipient_type] }}</i>
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
  </Placeholder>
</template>

<script>
import ConfirmButton from "@/components/inputs/ConfirmButton";
import Placeholder from "@/components/layout/Placeholder";
import ModalDialog from "@/components/layout/ModalDialog";
import SelectInput from "@/components/inputs/SelectInput";
import DropdownSelect from "@/components/inputs/DropdownSelect";
import IntegerInput from "@/components/inputs/IntegerInput";
import {Button, ModalButton} from "@/composables/modals";
import {loadGroupData, loadUserData} from "@/composables/auth";

export default {
  name: "PermissionList",
  components: {SelectInput, Placeholder, ModalDialog, ConfirmButton, DropdownSelect, IntegerInput},
  inject: ["groups", "users", "availableSchemas"],
  props: {
    recipientType: {
      type: String,
      required: false,
      default: null,
      validator(value) {
        return ["Group", "User"].includes(value);
      }
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
      }
    },
    objectId: {
      type: Number,
      required: false,
      default: null,
    }
  },
  data() {
    return {
      availableGroups: {},
      availableUsers: {},
      permissions: [],
      selected: [],
      loading: true,
      recipientIcons: {
        Group: "group",
        User: "person"
      },
      objectIcons: {
        Schema: "namespace",
        Entity: "table_rows",
        Group: "group"
      },
      toggleButton: new Button({
        icon: "add",
        text: "Grant new permission",
        css: "btn-outline-primary"
      }),
      modalButtons: [
        new ModalButton({
          callback: this.onAddition,
          icon: "add",
          text: "Grant",
          css: "btn-primary"
        })],
      permOptions: [
        {
          value: "SU",
          text: "Superuser"
        },
        {
          value: "UM",
          text: "User Management"
        },
        {
          value: "SCH_C",
          text: "Schema: Create"
        },
        {
          value: "SCH_U",
          text: "Schema: Update"
        },
        {
          value: "SCH_D",
          text: "Schema: Delete"
        },
        {
          value: "SCH_R",
          text: "Schema: Read"
        },
        {
          value: "ENT_C",
          text: "Entity: Create"
        },
        {
          value: "ENT_U",
          text: "Entity: Update"
        },
        {
          value: "ENT_D",
          text: "Entity: Delete"
        },
        {
          value: "ENT_R",
          text: "Entity: Read"
        }
      ],
      recipientOptions: [
        {
          value: "Group"
        },
        {
          value: "User"
        }
      ],
      recipientNameOptions: [],
      newPermData: {}
    }
  },
  computed: {
    availablePermissions() {
      if (this.objectType === "Group") {
        return this.permOptions.filter(x => x.value === "UM");
      }
      if (this.objectType === "Schema") {
        return this.permOptions.filter(x => /^SCH_[UR]|ENT_[CRUD]/.test(x.value));
      }
      if (this.objectType === "Entity") {
        return this.permOptions.filter(x => /^ENT_[UR]/.test(x.value));
      }
      return this.permOptions;
    },
    secondColumnName() {
      if (this.recipientId) {
        return "Object";
      }
      if (this.objectType) {
        return "Who";
      }
      return "?";
    },
    recipientName() {
      if (this.recipientType === "Group") {
        return this.availableGroups[this.recipientId]?.name;
      }
      return this.availableUsers[this.recipientId]?.username;
    },
    objectTypeOptions() {
      const nochoice = {value: null, text: "(none)"};
      if (this.newPermData.permission === "SU") {
        return [nochoice];
      }
      if (this.newPermData.permission === "UM") {
        return [nochoice, {value: "Group"}];
      }
      if (/^SCH_[UR]/.test(this.newPermData.permission)) {
        return [{value: "Schema"}];
      }
      if (/^ENT_[CD]/.test(this.newPermData.permission)) {
        return [{value: "Schema"}];
      }
      if (/^ENT_[UR]/.test(this.newPermData.permission)) {
        return [{value: "Entity"}, {value: "Schema"}];
      }
      return [nochoice, {value: "Group"}, {value: "Entity"}, {value: "Schema"}];
    },
    objectIdOptions() {
      if (this.newPermData.objType === "Group") {
        return Object.values(this.availableGroups).map(x => {
          return {value: x.id, text: x.name}
        });
      }
      if (this.newPermData.objType === "Schema") {
        return this.availableSchemas.map(x => {
          return {value: x.id, text: x.name}
        });
      }
      return []
    }
  },
  watch: {
    async recipientId() {
      await this.load();
      this.resetNewPermData();
    },
    async objectId() {
      await this.load();
      this.resetNewPermData();
    },
    async objectType() {
      await this.load();
      this.resetNewPermData();
    },
    async recipientType() {
      await this.load();
      this.resetNewPermData();
    }
  },
  async activated() {
    let response;
    if (this.groups) {
      this.availableGroups = this.groups;
    } else {
      response = await loadGroupData(this.$api);
      this.availableGroups = response[0];
    }
    if (this.users) {
      this.availableUsers = this.users;
    } else {
      this.availableUsers = await loadUserData(this.$api);
    }
    await this.load();
    this.resetNewPermData();
  },
  methods: {
    resetNewPermData() {
      this.newPermData = {
        permission: null,
        recipientType: this.recipientType,
        recipientName: this.recipientName,
        objType: this.objectType,
        objId: this.objectId
      }
      this.updateRecipientNameOptions();
    },
    updateRecipientNameOptions() {
      if (this.newPermData.recipientType == "Group") {
        this.recipientNameOptions = Object.values(this.availableGroups).map(x => {
          return {value: x.name}
        });
      } else if (this.newPermData.recipientType == "User") {
        this.recipientNameOptions = Object.values(this.availableUsers).map(x => {
          return {value: x.username}
        });
      } else {
        this.recipientNameOptions = [];
      }
    },
    isPermissionInherited(perm) {
      if (this.recipientType && this.recipientType === perm.recipient_type && this.recipientName === perm.recipient_name) {
        return false;
      }
      if (this.objectType && this.objectType === perm.obj_type && this.objectId === perm.obj_id) {
        return false;
      }
      return true;
    },
    async load() {
      this.loading = true;
      if ((this.recipientType && this.recipientId) || (this.objectType && this.objectId)) {
        this.permissions = await this.$api.getPermissions({
          recipientType: this.recipientType,
          recipientId: this.recipientId,
          objType: this.objectType,
          objId: this.objectId
        });
      } else {
        this.permissions = [];
      }
      this.selected = [];
      this.loading = false;
    },
    getObjectName(perm) {
      if (perm.obj_type === "Group") {
        return this.availableGroups[perm.obj_id].name;
      }
      if (perm.obj_type === "User") {
        return this.availableUsers[perm.obj_id].username;
      }
      if (perm.obj_type === "Schema") {
        return this.availableSchemas.filter(x => x.id === perm.obj_id).map(x => x.name)[0];
      }
      return perm.obj_id;
    },
    getObjectPermission(perm) {
      return this.permOptions.filter(x => x.value === perm.permission).map(x => x.text)[0];
    },
    onSelect() {
      const elems = document.getElementsByName("PermissionSelect");
      this.selected = Array.prototype.filter.call(elems, e => e.checked).map(e => e.value);
    },
    async onDelete() {
      await this.$api.revokePermissions({permissionIds: this.selected.map(x => parseInt(x))});
      await this.load();
    },
    async onAddition() {
      await this.$api.grantPermission(this.newPermData);
      await this.load();
      this.resetNewPermData();
    }
  }
}
</script>

<style scoped>

</style>