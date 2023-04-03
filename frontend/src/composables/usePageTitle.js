import { ref, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';

export default function usePageTitle(pageTitle) {
  const defaultTitle = "AIMAAS"; // used when no title is defined for given route
  const route = useRoute();
  const title = ref(defaultTitle);

  onMounted(() => { // used on first load to DOM
    title.value = pageTitle || route.meta.title || defaultTitle;
    document.title = title.value;
  });

  watch(() => route.meta.title, () => { // allows reactive changes
    title.value = pageTitle || route.meta.title || defaultTitle;
    document.title = title.value;
  });
}