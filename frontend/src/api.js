

class API{
    constructor(baseUrl){
        this.base = baseUrl;
    }

    async getSchemas({all=false, deletedOnly=false}={}){
        const params = new URLSearchParams();
        params.set('all', all);
        params.set('deleted_only', deletedOnly);
        return fetch(`${this.base}/schemas?${params.toString()}`);
    }

    async getEntities({
        schemaSlug,
        limit=10,
        offset=0, 
        all=false, 
        deletedOnly=false, 
        allFields=false, 
        meta=false, 
        filters={},
        orderBy='name',
        ascending=true,
    } = {}){
        const params = new URLSearchParams();
        params.set('limit', limit);
        params.set('offset', offset);
        params.set('all', all);
        params.set('all_fields', allFields);
        params.set('deletedOnly', deletedOnly);
        params.set('meta', meta);
        params.set('order_by', orderBy);
        params.set('ascending', ascending);
        for (const [filter, value] of Object.entries(filters)){
            params.set(filter, value);
        }
        return fetch(`${this.base}/dynamic/${schemaSlug}?${params.toString()}`);
    }

    async getEntity({schemaSlug, entityIdOrSlug, meta=false} = {}){
        const params = new URLSearchParams();
        params.set('meta', meta);
        return fetch(`${this.base}/dynamic/${schemaSlug}/${entityIdOrSlug}?${params.toString()}`);
    }

    async getRecentEntityChanges({schemaSlug, entityIdOrSlug} = {}){
        return fetch(`${this.base}/changes/entity/${schemaSlug}/${entityIdOrSlug}`);
    }

    async getEntityChangeDetails({schemaSlug, entityIdOrSlug, changeId} = {}){
        return fetch(`${this.base}/changes/entity/${schemaSlug}/${entityIdOrSlug}/${changeId}`);
    }

}

const api = new API(process.env.VUE_APP_API_BASE);
export {api}
