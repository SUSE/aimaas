<template>
  <li class="list-group-item">
    <div class="d-flex flex-row align-items-center">
      <div style="width: 3rem;">
        <button v-if="hasChildren(group.id)" class="btn btn-sm btn-light flex-grow-1" type="button"
                :data-bs-target="`#${collapseId}`" aria-expanded="false" data-bs-toggle="collapse"
                :aria-controls="collapseId" title="Expand list of sub-groups">
          <i class="eos-icons me-1">more_vert</i>
        </button>
      </div>
      <button class="btn btn-link" @click="changeGroup(group)">
        {{ group.name }}
      </button>


    </div>
    <div v-if="hasChildren(group.id)" class="collapse" :id="collapseId">
      <ul class="list-group">
        <GroupListItem :group="child" :groups="groups" :tree="tree"
                       v-for="child in childrenOf(group.id)" :key="child.id"
                       @groupSelected="changeGroup"/>
      </ul>
    </div>

  </li>
</template>

<script>
export default {
  name: "GroupListItem",
  emits: ["groupSelected"],
  inject: ["groups", "tree"],
  props: {
    group: {
      required: true,
      type: Object,
    }
  },
  computed: {
    collapseId() {
      return `collapse-${this.group.id}`;
    }
  },
  methods: {
    childrenOf(parentId) {
      return this.tree[parentId].map(i => this.groups[i]);
    },
    hasChildren(parentId) {
      return parentId in this.tree && this.tree[parentId].length > 0;
    },
    changeGroup(group){
      this.$emit('groupSelected', group);
    }
  }
}
</script>

<style scoped>

</style>