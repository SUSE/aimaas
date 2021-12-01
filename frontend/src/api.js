

class API{
    constructor(baseUrl){
        this.base = baseUrl;
    }

    async get_schemas({all=false, deletedOnly=false}={}){
        const params = new URLSearchParams();
        params.set('all', all)
        params.set('deleted_only', deletedOnly)
        return fetch(`${this.base}/schemas?${params.toString()}`)
    }

    async get_entities({
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
        params.set('limit', limit)
        params.set('offset', offset)
        params.set('all', all)
        params.set('all_fields', allFields)
        params.set('deletedOnly', deletedOnly)
        params.set('meta', meta)
        params.set('order_by', orderBy)
        params.set('ascending', ascending)
        for (const [filter, value] of Object.entries(filters)){
            params.set(filter, value)
        }
        return fetch(`${this.base}/dynamic/${schemaSlug}?${params.toString()}`)
    }
}

const api = new API(process.env.VUE_APP_API_BASE);
export {api}
