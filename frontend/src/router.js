import {createRouter, createWebHistory} from 'vue-router'
import SchemaCreate from "@/components/SchemaCreate.vue"
import Changes from "@/components/change_review/Changes";
import Entity from "@/components/Entity.vue"
import EntityBulkEdit from "@/components/EntityBulkEdit.vue";
import Schema from "@/components/Schema";
import SchemaList from "@/components/SchemaList";
import AuthManager from "@/components/auth/AuthManager";
import About from "@/components/help/About";

export const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/createSchema',
            component: SchemaCreate,
            name: 'schema-new',
            cached: true,
            meta: {
                title: 'Create Schema'
            }
        },
        {
            path: '/bulkEdit/:schemaSlug',
            component: EntityBulkEdit,
            name: 'bulk-edit',
            cached: true,
            meta: {
                title: "Edit Schemas"
            }
        },
        {
            path: '/schema/:schemaSlug',
            component: Schema,
            name: 'schema-view',
            cached: true,
            meta: {
                title: 'Schema Details'
            }
        },
        {
            path: '/schema/:schemaSlug/:entitySlug',
            component: Entity,
            name: 'entity-view',
            cached: false,
            meta: {
                title: 'Entity Details'
            }
        },
        {
            path: '/review',
            component: Changes,
            name: 'review-list',
            cached: true,
            meta: {
                title: 'Pending Reviews'
            }
        },
        {
            path: '/user-management',
            component: AuthManager,
            cached: true,
            name: 'auth-manager',
            meta: {
                title: 'User Management'
            }
        },
        {
            path: '/',
            component: SchemaList,
            name: 'schema-list',
            cached: true,
            meta: {
                title: 'All Schemas'
            }
        },
        {
            path: '/help/about',
            component: About,
            name: 'help-about',
            cached: true,
            meta: {
                title: 'About AIMAAS'
            }
        }
    ],
});
