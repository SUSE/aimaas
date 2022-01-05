import {reactive} from "vue";


class API {
    constructor(app) {
        console.debug(document);
        this.base = "/api";
        this.app = app;
        this.alerts = app.config.globalProperties.$alerts;
        this.loggedIn = null;
        this.token = null;
    }

    async _error_to_alert(details) {
        const message = details?.message || "Failed to process request";
        if (this.alerts) {
            this.alerts.push("danger", message);
        }
        console.error(message);
    }

    async _is_response_ok(response) {
        if (response.ok && response.status < 400) {
            return null;
        }

        let detail;
        try {
            detail = await response.json();
        } catch (error) {
            if (error instanceof SyntaxError) {
                throw new Error(response.statusText);
            }
            throw error;
        }
        if (Array.isArray(detail.detail)) {
            throw new Error(detail.detail.map(d => `${d.loc}: ${d.msg}`).join(", "));
        } else if (typeof detail.detail === "string") {
            throw new Error(detail.detail);
        } else {
            console.error("Response indicates a problem", detail);
            throw new Error("Failed to process request. See console for more details.");
        }
    }

    async _fetch({url, headers, body, method} = {}) {
        let allheaders = {"Content-Type": "application/json"};
        let encoded_body = null;
        allheaders = Object.assign(allheaders, headers || {});
        if (body instanceof FormData || typeof body === "string") {
            encoded_body = body;
        } else if (body) {
            encoded_body = JSON.stringify(body);
        }

        try {
            const response = await fetch(url, {
                method: method || 'GET',
                body: encoded_body,
                headers: allheaders
            });
            await this._is_response_ok(response);
            return await response.json();
        } catch (e) {
            this._error_to_alert(e);
            return null;
        }
    }

    async getSchemas({all = false, deletedOnly = false} = {}) {
        const params = new URLSearchParams();
        params.set('all', all);
        params.set('deleted_only', deletedOnly);
        return this._fetch({url: `${this.base}/schemas?${params.toString()}`});
    }

    async getSchema({slugOrId} = {}) {
        return this._fetch({url: `${this.base}/schemas/${slugOrId}`});
    }

    async createSchema({body} = {}) {
        const response = await this._fetch({
            url: `${this.base}/schemas`,
            method: 'POST',
            body: body,
        });
        if (response !== null) {
            this.alerts.push("success", `Schema created: ${body.name}`);
        }
        return response;
    }

    async updateSchema({schemaSlug, body} = {}) {
        const response = await this._fetch({
            url: `${this.base}/schemas/${schemaSlug}`,
            method: "PUT",
            body: body
        });
        if (response !== null) {
            this.alerts.push("success", `Schema updated: ${schemaSlug}`);
        }
        return response;
    }

    async deleteSchema({slugOrId} = {}) {
        const response = await this._fetch({
            url: `${this.base}/schemas/${slugOrId}`,
            method: 'DELETE'
        });
        if (response !== null) {
            this.alerts.push("success", `Schema deleted: ${response.name}`);
        }
        return response;
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
        return this._fetch({
            url: `${this.base}/${schemaSlug}?${params.toString()}`
        });
    }

    async getEntity({schemaSlug, entityIdOrSlug, meta = false} = {}) {
        const params = new URLSearchParams();
        params.set('meta', meta);
        return this._fetch({
            url: `${this.base}/${schemaSlug}/${entityIdOrSlug}?${params.toString()}`
        });
    }

    async createEntity({schemaSlug, body} = {}) {
        const response = await this._fetch({
            url: `${this.base}/${schemaSlug}`,
            method: 'POST',
            body: body
        });
        if (response !== null) {
            this.alerts.push("success", `Entity created: ${body.name}`);
        }
        return response;
    }

    async updateEntity({schemaSlug, entityIdOrSlug, body} = {}) {
        const response = await this._fetch({
            url: `${this.base}/${schemaSlug}/${entityIdOrSlug}`,
            method: 'PUT',
            body: body
        });
        if (response !== null) {
            this.alerts.push("success", `Entity updated: ${entityIdOrSlug}`);
        }
        return response;
    }

    async deleteEntity({schemaSlug, entityIdOrSlug} = {}) {
        const response = await this._fetch({
            url: `${this.base}/${schemaSlug}/${entityIdOrSlug}`,
            method: 'DELETE'
        });
        if (response !== null) {
            this.alerts.push("success", `Entity deleted: ${response.name}`);
        }
        return response;
    }

    async getChangeRequests({schemaSlug, entityIdOrSlug} = {}) {
        let url = `${this.base}/changes/schema/${schemaSlug}`;
        if (entityIdOrSlug) {
            url = `${this.base}/changes/entity/${schemaSlug}/${entityIdOrSlug}`;
        }
        return this._fetch({url: url});
    }

    async getChangeRequestDetails({objectType, changeId} = {}) {
        let url = `${this.base}/changes/detail/${objectType}/${changeId}`;
        return this._fetch({url: url,})
    }

    async getPendingChangeRequests() {
        let url = `${this.base}/changes/pending?all=true`;
        return this._fetch({url: url});
    }

    async reviewChanges({changeId, verdict, comment=null} = {}) {
        const response = await this._fetch({
            url: `${this.base}/changes/review/${changeId}`,
            method: "POST",
            body: {
                result: verdict,
                comment: comment || null,
            }
        });
        if (response) {
            this.alerts.push("success", `Change request ${changeId} successfully reviewed.`);
        }
        return response;
    }

    async login({username, password} = {}) {
        const url = `${this.base}/login`;
        const body = `username=${username}&password=${password}`;
        const response = await this._fetch({
            url: url,
            method: 'POST',
            body: encodeURI(body),
            headers: {'Content-Type': 'application/x-www-form-urlencoded'}
        });
        this.loggedIn = username;
        this.token = response.access_token;
        this.alerts.push("success", `Welcome back, ${username}.`);
        return response;
    }

    async getUsers() {
        return await this._fetch({url: `${this.base}/users`});
    }

    async getGroups() {
        return await this._fetch({url: `${this.base}/groups`});
    }

    async getMembers({groupId}) {
        return await this._fetch({url: `${this.base}/groups/${groupId}/members`});
    }
}


export default {
    install: (app) => {
        app.config.globalProperties.$api = reactive(new API(app));
    }
}