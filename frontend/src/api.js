

class API {
    constructor(baseUrl) {
        this.base = baseUrl;
    }

    async _is_response_ok(response) {
        if (response.ok && response.status < 400) {
            return null;
        }

        let detail = {msg: "Something went wrong"};
        try {
             detail = await response.json();
        }
        catch (e) {
            console.error("Failed to fetch data from API", e);
        }
        throw detail;
    }

    async getAttributes() {
        const response = await fetch(`${this.base}/attributes`);
        try {
            this._is_response_ok(response);
            return await response.json()
        }
        catch (e) {
            // TODO: Do something else
        }
    }

    async getSchemas({ all = false, deletedOnly = false } = {}) {
        const params = new URLSearchParams();
        params.set('all', all);
        params.set('deleted_only', deletedOnly);
        const response = await fetch(`${this.base}/schemas?${params.toString()}`);
        try {
            this._is_response_ok(response);
            return await response.json()
        }
        catch (e) {
            // TODO: Do something else
        }
    }

    async getSchema({ slugOrId } = {}) {
        const response = await fetch(`${this.base}/schemas/${slugOrId}`);
        try {
            this._is_response_ok(response);
            return await response.json()
        }
        catch (e) {
            console.error(e);
            throw e;
            // TODO: Do something else
        }
    }

    async createSchema({ body } = {}) {
        return fetch(`${this.base}/schemas`, {
            method: 'POST',
            body: JSON.stringify(body),
            headers: { "Content-Type": "application/json" },
        });
    }

    async updateSchema({ schemaSlug, body } = {}) {
        return fetch(
            `${this.base}/schemas/${schemaSlug}`,
            {
                method: "PUT",
                body: JSON.stringify(body),
                headers: { "Content-Type": "application/json" },
            }
        );
    }

    async getEntities({
        schemaSlug,
        limit = 10,
        offset = 0,
        all = false,
        deletedOnly = false,
        allFields = false,
        meta = false,
        filters = {},
        orderBy = 'name',
        ascending = true,
    } = {}) {
        const params = new URLSearchParams();
        params.set('limit', limit);
        params.set('offset', offset);
        params.set('all', all);
        params.set('all_fields', allFields);
        params.set('deletedOnly', deletedOnly);
        params.set('meta', meta);
        params.set('order_by', orderBy);
        params.set('ascending', ascending);
        for (const [filter, value] of Object.entries(filters)) {
            params.set(filter, value);
        }
        const response = await fetch(`${this.base}/dynamic/${schemaSlug}?${params.toString()}`);
        try {
            this._is_response_ok(response);
            return await response.json();
        }
        catch (e) {
            console.error("Failed to get entities", e, response);
            throw e;
            // TODO: Do something else
        }
    }

    async getEntity({ schemaSlug, entityIdOrSlug, meta = false } = {}) {
        const params = new URLSearchParams();
        params.set('meta', meta);
        return fetch(`${this.base}/dynamic/${schemaSlug}/${entityIdOrSlug}?${params.toString()}`);
    }

    async createEntity({ schemaSlug, body } = {}) {
        return fetch(`${this.base}/dynamic/${schemaSlug}`, {
            method: 'POST',
            body: JSON.stringify(body),
            headers: { "Content-Type": "application/json" },
        })
    }

    async updateEntity({ schemaSlug, entityIdOrSlug, body } = {}) {
        return fetch(`${this.base}/dynamic/${schemaSlug}/${entityIdOrSlug}`, {
            method: 'PUT',
            body: JSON.stringify(body),
            headers: { "Content-Type": "application/json" },
        })
    }

    async getRecentEntityChanges({ schemaSlug, entityIdOrSlug } = {}) {
        return fetch(`${this.base}/changes/entity/${schemaSlug}/${entityIdOrSlug}`);
    }

    async getEntityChangeDetails({ schemaSlug, entityIdOrSlug, changeId } = {}) {
        return fetch(`${this.base}/changes/entity/${schemaSlug}/${entityIdOrSlug}/${changeId}`);
    }

    async reviewChanges({ changeId, verdict, changeObject, changeType, comment } = {}) {
        return fetch(`${this.base}/changes/review/${changeId}`, {
            method: "POST",
            body: JSON.stringify({
                result: verdict,
                change_object: changeObject,
                change_type: changeType,
                comment: comment || null,
            }),
            headers: { "Content-Type": "application/json" },
        });
    }

}

const api = new API(process.env.VUE_APP_API_BASE);
export { api }
