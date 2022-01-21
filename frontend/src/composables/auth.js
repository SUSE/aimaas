export async function loadGroupData(api) {
  const response = await api.getGroups();
  const groups = {};
  const tree = {};

  for (let group of response) {
    groups[group.id] = group;
    if (!(group.parent_id in tree)) {
      tree[group.parent_id] = [];
    }
    tree[group.parent_id].push(group.id);
  }

  return [groups, tree];
}


export async function loadUserData(api) {
  const response = await api.getUsers();
  const users = {};
  for (const user of response) {
    users[user.id] = user;
  }
  return users;
}