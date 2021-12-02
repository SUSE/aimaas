import { createRouter, createWebHistory } from 'vue-router'
import EntityDetail from './components/EntityDetail.vue';
import EntityList from "./components/EntityList.vue";
// import CreateSchema from "./components/CreateSchema.vue"
// import CreateEntity from "./components/CreateEntity.vue"
// import EditSchema from "./components/EditSchema.vue";
// import EditEntity from "./components/EditEntity.vue";
// import EntityChangeDetails from "./components/EntityChangeDetails.vue";
// import SchemaDetails from "./components/SchemaDetails.vue";

export const router = createRouter({
    history: createWebHistory(),
    routes: [
        // { path: '/createSchema', component: CreateSchema},
        // { path: '/:schemaSlug', component: SchemaDetails},
        // { path: '/changes/entity/:changeId', component: EntityChangeDetails},
        // { path: '/edit/:schemaSlug/:entitySlug', component: EditEntity},
        // { path: '/edit/:slugOrId', component: EditSchema},
        // { path: '/:schemaSlug/entities/new', component: CreateEntity },
        { path: '/:schemaSlug/:entityIdOrSlug', component: EntityDetail },
        { path: '/', component: EntityList },
    ],
});