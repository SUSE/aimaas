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

  const fetchGroupData = async () => {
    const response = await api.getGroups();
  
    for (let group of (response || [])) {
      groups.value[group.id] = group;
    }
  }

  const loadGroupData = async () => {
    if (Object.values(groups.value).length === 0) {
      await fetchGroupData()
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
  
  const fetchUserData = async () => {
    const response = await api.getUsers();
    for (const user of (response || [])) {
      users.value[user.id] = user;
    }
  }

  const loadUserData = async () => {
    if (Object.values(users.value).length === 0) {
      await fetchUserData();
    }
  }

  const activateUser = async (username) => {
    const result = await api.activate_user({username: username});
    if (result != null) {
      Object.values(users.value).forEach(user => {
        if(user.username === username) {
          user.is_active = true;
        }
      });
    }
  }

  const deactivateUser = async (username) => {
    const result = await api.deactivate_user({username: username});
    if (result !== null) {
      Object.values(users.value).forEach(user => {
        if(user.username === username) {
          user.is_active = false;
        }
      });
    }
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
