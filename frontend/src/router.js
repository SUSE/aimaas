import { createRouter, createWebHistory } from 'vue-router'
import SchemaCreate from "@/components/SchemaCreate.vue"
import Entity from "@/components/Entity.vue"
import EntityChangeDetails from "@/components/EntityChangeDetails.vue";
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
            path: '/:schemaSlug/:entitySlug',
            component: Entity,
            name: 'entity-view'
        },
        {
            path: '/',
            component: SchemaList,
            name: 'schema-list'
        },
    ],
});