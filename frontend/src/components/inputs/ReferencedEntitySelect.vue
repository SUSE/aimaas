<template>
  <BaseInput :label="label" :args="args" :vertical="false" :required="required">
    <template v-slot:helptext>
      Click button to open the selection dialog.
    </template>
    <template v-slot:field>
      <ul class="list-group">
        <li class="list-group-item d-flex justify-content-between align-items-center"
            v-for="e in selected" :key="e.id">
          <span>
            <router-link :to="{name: 'entity-view', params: {schemaSlug: fkSchema.slug, entitySlug: e.slug}}">
              {{ e.name }}
            </router-link>
          </span>
          <button class="btn btn-outline-cta" type="button"
                  data-ts-toggle="tooltip" title="Remove" @click="onClear(e.id)">
            <i class="eos-icons">backspace</i>
          </button>
        </li>
      </ul>
      <ModalDialog :modal-buttons="modalButtons" :toggle-button="toggleButton"
                   :modal-title="`Select entity ${selectType}`">
        <template v-slot:content>
          <EntityList :schema="fkSchema" ref="editor" :select-type="selectType"/>
        </template>
      </ModalDialog>
    </template>
  </BaseInput>
</template>

<script>
import {Button, ModalButton} from "@/composables/modals";
import BaseInput from "@/components/layout/BaseInput";
import EntityList from "@/components/EntityList";
import ModalDialog from "@/components/layout/ModalDialog";

export default {
  name: "ReferencedEntitySelect",
  components: {BaseInput, EntityList, ModalDialog},
  emits: ["changed", "selected", "update:modelValue"],
  props: ["args", "label", "modelValue", "fkSchemaId", "selectType", "required"],
  inject: ["activeSchema", "availableSchemas"],
  data() {
    return {
      loading: true,
      selected: [],
      modalId: `entitySelectModal-${this.label}`,
      toggleButton: new Button({
        css: "btn-outline-primary w-100 mt-1",
        icon: "checklist",
        text: `Select ${this.selectType}`
      }),
      modalButtons: [
          new ModalButton({
            css: "btn-primary",
            icon: "subdirectory_arrow_left",
            text: "Apply",
            callback: this.onSelect
          })
      ],
      currentEntitySlug: this.$route.params.entitySlug,
    }
  },
  activated() {
    this.getSelected();
  },
  computed: {
    fkSchema() {
      for (const schema of this.availableSchemas) {
        if (schema.id === this.fkSchemaId) {
          return schema;
        }
      }
      return null;
    }
  },
  methods: {
    getSelected() {
      if (!this.modelValue) {
        return;
      }
      if (this.currentEntitySlug !== this.$route.params.entitySlug) {
        this.selected.length = 0;
        this.currentEntitySlug = this.$route.params.entitySlug;
      }

      const preselectedIds = this.selected.map(x => x.id);
      let toQuery = this.modelValue;
      if (!Array.isArray(this.modelValue)) {
        toQuery = [this.modelValue];
      }

      toQuery.map(i => {
        if (!preselectedIds.includes(i)) {
          this.$api.getEntity({
            schemaSlug: this.fkSchema.slug,
            entityIdOrSlug: i
          }).then(response => {
            this.selected.push(response);
          });
        }
      });
    },
    onSelect() {
      if (this.selectType === 'single') {
        this.selected.splice(0, this.selected.length);
      }
      const preselectedIds = this.selected.map(x => x.id);
      for (const s of this.$refs.editor.getSelected()) {
        if (!preselectedIds.includes(s.id)) {
          this.selected.push(s);
        }
      }
      if (this.selectType === 'single') {
        this.$emit("update:modelValue", this.selected[0].id);
      } else {
        this.$emit("update:modelValue", this.selected.map(s => s.id));
      }
      this.$emit("changed");
    },
    onClear(eId) {
      if (this.selectType === 'single') {
        this.selected.length = 0;
        this.$emit("update:modelValue", null);
      } else {
        this.selected = this.selected.filter(x => x.id !== eId);
        this.$emit("update:modelValue", this.selected.map(s => s.id));
      }
      this.$emit("changed");
    }
  },
  watch: {
    modelValue() {
      this.getSelected();
    },
    selected: {
      handler: "getSelected",
      immediate: true
    }
  }
};
</script>