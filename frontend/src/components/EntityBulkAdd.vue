<template>
  <div v-for="(form, index) in entityForms" :key="form.props.id">
    <div :id="`form-${index}`">
      <div :class="`${entityForms.length < 2 && 'd-none'} ${index > 0 && 'mt-5 border-top border-light'} row`">
        <div class="col">
          <button type="button" :class="`btn-close float-end ${index > 0 ? 'my-3': 'mb-3'}`"
                  @click="closeForm(form.props.id)"/>
        </div>
      </div>
      <component :is="form.component" @save-all="saveAll" v-bind="form.props" :ref="form.props.id"/>
    </div>
  </div>
  <div class="container mt-2">
    <button class="btn btn-outline-secondary w-100" @click="addNewItem">
      <i class='eos-icons'>add_circle</i>
      Add more
    </button>
  </div>
</template>

<script>
import EntityForm from "@/components/inputs/EntityForm.vue";
import {markRaw} from "vue";

export default {
  name: "EntityBulkAdd",
  components: {EntityForm},
  props: {
    schema: {
      type: Object,
      required: true
    },
    attributes: {
      type: Object,
      required: true,
    }
  },
  data() {
    return {
      entityForms: [this.generateEntityForm()]
    }
  },
  methods: {
    async saveAll() {
      let successIds = [];
      const promises = Object.entries(this.$refs)
          .filter(x => x[0].startsWith("entity-form-"))
          .map(async x => {
            const resp = await x[1][0].createEntity();
            if (resp?.id) {
              successIds.push(x[0]);
            }
          });
      await Promise.all(promises);
      if (this.entityForms.length > 1) {
        this.entityForms = this.entityForms.filter(e => !successIds.includes(e.props.id));
      } else if (successIds.length) {
        this.entityForms = [this.generateEntityForm()];
      }
    },
    async addEntityForm() {
      this.entityForms.push(this.generateEntityForm());
    },
    addNewItem() {
      this.addEntityForm().then(() => {
        document.getElementById(`form-${this.entityForms.length - 1}`).scrollIntoView();
      });
    },
    generateEntityForm() {
      return {
        component: markRaw(EntityForm),
        props: {
          id: `entity-form-${(this.entityForms && this.entityForms.length) || 0}`,
          attributes: this.attributes,
          schema: this.schema,
          batchMode: true,
        }
      }
    },
    closeForm(formId) {
      this.entityForms = this.entityForms.filter(e => formId !== e.props.id);
    }
  }
}

</script>

<style scoped>

</style>