<template>
  <template v-for="(form, index) in entityForms" :key="form.ref">
    <div :id="`form-${index}`">
      <div :class="`${entityForms.length < 2 && 'd-none'} ${index > 0 && 'mt-5 border-top border-light'} row`">
        <div class="col">
          <button type="button" :class="`btn-close float-end ${index > 0 ? 'my-3': 'mb-3'}`"
                  @click="closeForm(`form-${index}`, form.ref)"/>
        </div>
      </div>
      <component :is="form.component" @save-all="saveAll" v-bind="form.props"
                 :ref="el => { entityFormRefs[form.ref] = el }"/>
    </div>
  </template>
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
import _cloneDeep from "lodash/cloneDeep";

const props = defineProps({
  schema: {
    type: Object,
    required: true
  },
  entity: {
    type: Object,
    required: true,
  }
});

const entityData = ref(prepEntity());
const entityForms = ref([generateEntityForm(0)]);
const entityFormRefs = ref([]);

function generateEntityForm(id) {
  return {
    component: markRaw(EntityForm),
    ref: `entity-form-${id}`,
    props: {
      entity: entityData,
      schema: props.schema,
      batchMode: true,
      showAttributeCheckboxes: true,
    }
  }
}

async function saveAll() {
  let successfullySaved = [];
  const promises = Object.entries(entityFormRefs.value).map(ref => saveSingle(ref));
  Promise.all(promises).then(responses => {
    responses.forEach(resp => {
      if (resp?.id) {
        const ref = Object.entries(entityFormRefs.value)
            .find(ref => ref[1].editEntity.slug === resp.slug);

        successfullySaved.push(ref[0]);
        clearEntityForm(ref);
      }
    });
    entityFormRefs.value = [];
    const forms = entityForms.value.filter(e => !successfullySaved.includes(e.ref));
    entityForms.value = forms.length ? forms : [generateEntityForm(0)];
  });
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

function closeForm(formId, refName) {
  const form = document.getElementById(formId);
  form.style.transition = "0.5s linear all";
  form.style.opacity = "0";

  setTimeout(() => {
    entityForms.value = entityForms.value.filter(e => refName !== e.ref);
    entityFormRefs.value = entityFormRefs.value.filter(ref => ref[0] !== refName);
  }, 500);
}

function prepEntity() {
  let entityCopy = _cloneDeep(props.entity);
  entityCopy.name = null;
  entityCopy.slug = null;
  delete entityCopy.id;
  delete entityCopy.deleted;

  return entityCopy;
}

</script>