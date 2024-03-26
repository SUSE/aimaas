import { ref,computed } from 'vue';
import { api } from '@/composables/api';

const groups = ref({});
const users = ref({});

export const useAuthStore = () => {

  const tree = computed(() => {
    const computedTree = {};
    for (let group of Object.values(groups.value)) {
      if (!(group.parent_id in computedTree)) {
        computedTree[group.parent_id] = [];
      }

      if (computedTree[group.parent_id].indexOf(group.id) < 0 ) {
        computedTree[group.parent_id].push(group.id);
      }
    }

    return computedTree;
  })

  const loadGroupData = async () => {
    const response = await api.getGroups();
  
    for (let group of (response || [])) {
      groups.value[group.id] = group;
    }
  }

  const updateGroup = async (groupId, groupData) => {
    try {
      const response = await api.updateGroup({ groupId: groupId, body: groupData });
      groups.value[response.id] = response;
    } catch (err) {
      console.error(err);
    }
  }

  const createGroup = async (groupData) => {
    try {
      const response = await api.createGroup({ body: groupData });
      groups.value[response.id] = response;
    } catch (err) {
      console.error(err);
    }
  }

  const deleteGroup = async (groupId) => {
    const response = await api.deleteGroup({
      groupId: groupId,
    });
    if (response) {
      delete groups.value[groupId]
    }
  }
  
  const loadUserData = async () => {
    const response = await api.getUsers();
    for (const user of (response || [])) {
      users.value[user.id] = user;
    }
  }

  const activateUser = async (username) => {
    await api.activate_user({username: username});
    Object.values(users.value).forEach(user => {
      if(user.username === username) {
        user.is_active = !user.is_active
      }
    });
  }

  const deactivateUser = async (username) => {
    await api.deactivate_user({username: username});
    Object.values(users.value).forEach(user => {
      if(user.username === username) {
        user.is_active = !user.is_active
      }
    });
  }

  return {
    groups,
    users,
    tree,
    loadGroupData,
    createGroup,
    updateGroup,
    deleteGroup,
    loadUserData,
    activateUser,
    deactivateUser,
  }
}
