import { createRouter, createWebHistory } from 'vue-router'
import EntityDetail from './components/EntityDetail.vue';
import EntityList from "./components/EntityList.vue";
// import CreateSchema from "./components/CreateSchema.vue"
import EntityEdit from "./components/EntityEdit.vue"
// import EditSchema from "./components/EditSchema.vue";
import EntityCreate from "./components/EntityCreate.vue";
// import EntityChangeDetails from "./components/EntityChangeDetails.vue";
// import SchemaDetails from "./components/SchemaDetails.vue";

export const router = createRouter({
    history: createWebHistory(),
    routes: [
        // { path: '/createSchema', component: CreateSchema},
        // { path: '/:schemaSlug', component: SchemaDetails},
        // { path: '/changes/entity/:changeId', component: EntityChangeDetails},
        { path: '/edit/:schemaSlug/:entitySlug', component: EntityEdit},
        // { path: '/edit/:slugOrId', component: EditSchema},
        { path: '/:schemaSlug/entities/new', component: EntityCreate },
        { path: '/:schemaSlug/:entityIdOrSlug', component: EntityDetail },
        { path: '/', component: EntityList },
    ],
});