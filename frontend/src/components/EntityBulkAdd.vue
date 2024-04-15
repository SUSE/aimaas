<template>
  <div v-for="(form, index) in entityForms" :key="form.props.id">
    <div :id="`form-${index}`">
      <div :class="`${entityForms.length < 2 && 'd-none'} ${index > 0 && 'mt-5 border-top border-light'} row`">
        <div class="col">
          <button type="button" :class="`btn-close float-end ${index > 0 ? 'my-3': 'mb-3'}`"
                  @click="closeForm(form.props.id)"/>
        </div>
      </div>
      <component :is="form.component" @save-all="saveAll" v-bind="form.props"
                 :ref="el => { refs[`entity-form-${index}`] = el }"/>
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
export default {
  name: 'EntityBulkAdd'
}
</script>

<script setup>
import {markRaw, ref} from "vue";
import EntityForm from "@/components/inputs/EntityForm.vue";

const props = defineProps({
  schema: {
    type: Object,
    required: true
  },
  attributes: {
    type: Object,
    required: true,
  }
});

const entityForms = ref([generateEntityForm(0)]);
const refs = ref([]);

function generateEntityForm(id) {
  return {
    component: markRaw(EntityForm),
    props: {
      id: `entity-form-${id}`,
      attributes: props.attributes,
      schema: props.schema,
      batchMode: true,
    }
  }
}

async function saveAll() {
  let successIds = [];
  const promises = Object.entries(refs.value).map(async x => {
    const refName = x[0];
    const component = x[1];

    if (refName && component) {
      const resp = await component.createEntity();
      if (resp?.id) {
        successIds.push(refName);
        component.editEntity.name = null;
        component.editEntity.slug = null;
      }
    }
  });

  await Promise.all(promises);
  const forms = entityForms.value.filter(e => !successIds.includes(e.props.id));
  entityForms.value = forms.length ? forms : [generateEntityForm(0)];
}

async function addEntityForm() {
  entityForms.value.push(generateEntityForm(entityForms.value.length));
}

function addNewItem() {
  addEntityForm().then(() => {
    document.getElementById(`form-${entityForms.value.length - 1}`).scrollIntoView();
  });
}

function closeForm(formId) {
  entityForms.value = entityForms.value.filter(e => formId !== e.props.id);
}
</script>