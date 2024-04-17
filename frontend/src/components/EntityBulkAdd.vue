<template>
  <div v-for="(form, index) in entityForms" :key="form.ref">
    <div :id="`form-${index}`">
      <div :class="`${entityForms.length < 2 && 'd-none'} ${index > 0 && 'mt-5 border-top border-light'} row`">
        <div class="col">
          <button type="button" :class="`btn-close float-end ${index > 0 ? 'my-3': 'mb-3'}`"
                  @click="closeForm(form.ref)"/>
        </div>
      </div>
      <component :is="form.component" @save-all="saveAll" v-bind="form.props"
                 :ref="el => { entityFormRefs[form.ref] = el }"/>
    </div>
  </div>
  <div class="container mt-2">
    <button class="btn btn-outline-secondary w-100" @click="addNewItem">
      <i class='eos-icons'>add_circle</i>
      Add more
    </button>
  </div>
</template>

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
const entityFormRefs = ref([]);

function generateEntityForm(id) {
  return {
    component: markRaw(EntityForm),
    ref: `entity-form-${id}`,
    props: {
      attributes: props.attributes,
      schema: props.schema,
      batchMode: true,
    }
  }
}

async function saveAll() {
  let successfullySaved = [];
  const promises = Object.entries(entityFormRefs.value).map(async ref => {
    const response = await saveSingle(ref);
    if (response?.id) {
      successfullySaved.push(ref[0]);
      clearEntityForm(ref);
    }
  });

  await Promise.all(promises);
  entityFormRefs.value = [];
  const forms = entityForms.value.filter(e => !successfullySaved.includes(e.ref));
  entityForms.value = forms.length ? forms : [generateEntityForm(0)];
}

async function saveSingle(entityFormComponentRef) {
  const entityForm = entityFormComponentRef[1];

  if (entityForm) {
    return await entityForm.createEntity();
  }
}

function clearEntityForm(entityFormComponentRef) {
  const entityForm = entityFormComponentRef[1];

  if (entityForm) {
    entityForm.editEntity.name = null;
    entityForm.editEntity.slug = null;
  }
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
  entityForms.value = entityForms.value.filter(e => formId !== e.ref);
}
</script>