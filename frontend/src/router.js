import { createRouter, createWebHistory } from 'vue-router'
import EntityDetail from './components/EntityDetail.vue';
// import EntityList from "./components/EntityList.vue";
import SchemaCreate from "./components/SchemaCreate.vue"
import EntityEdit from "./components/EntityEdit.vue"
// import EditSchema from "./components/EditSchema.vue";
import EntityCreate from "./components/EntityCreate.vue";
import EntityChangeDetails from "./components/EntityChangeDetails.vue";
// import SchemaDetail from "./components/SchemaDetail.vue";
import Schema from "@/components/Schema";
import SchemaList from "@/components/SchemaList";

export const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/createSchema',
            component: SchemaCreate,
            name: 'schema-new'
        },
        {
            path: '/:schemaSlug',
            component: Schema,
            name: 'schema-view'
        },
        {
            path: '/changes/entity/:schema/:entity/:changeId',
            component: EntityChangeDetails,
            name: 'entity-changes'
        },
        {
            path: '/edit/:schemaSlug/:entitySlug',
            component: EntityEdit,
            name: 'entity-edit'
        },
        // { path: '/edit/:slugOrId', component: EditSchema},
        {
            path: '/:schemaSlug/entities/new',
            component: EntityCreate,
            name: 'entity-new'
        },
        {
            path: '/:schemaSlug/:entityIdOrSlug',
            component: EntityDetail,
            name: 'entity-view'
        },
        {
            path: '/',
            component: SchemaList,
            name: 'schema-list'
        },
    ],
});