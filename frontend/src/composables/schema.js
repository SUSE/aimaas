import {ref} from 'vue';
import {api} from '@/composables/api';
import {useRoute} from 'vue-router';

export const useSchema = () => {
  const activeSchema = ref(null);
  const route = useRoute();
  const getSchema = async () => {
    const slug = route.params.schemaSlug;
    if (slug) {
      activeSchema.value = await api.getSchema({slugOrId: slug});
    }
  }

  return {
    activeSchema,
    getSchema
  }
}