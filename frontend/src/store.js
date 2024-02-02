import {ref} from 'vue';

export const updateEntityListCount = ref(0);
export const updateEntityList = () => updateEntityListCount.value++;