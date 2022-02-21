import {reactive} from "vue";


class API {
    constructor(app) {
        console.debug(document);
        this.base = "/api";
        this.storageprefix = "aimaas";
        this.app = app;
        this.alerts = app.config.globalProperties.$alerts;
    }

    set token(val) {
        if (val) {
            window.localStorage.setItem(this.storageprefix + "Token", val);
        } else {
            window.localStorage.removeItem(this.storageprefix + "Token");
        }
    }

    get token() {
        return window.localStorage.getItem(this.storageprefix + "Token");
    }

    set loggedIn(val) {
        if (val) {
            window.localStorage.setItem(this.storageprefix + "User", val);
        } else {
            window.localStorage.removeItem(this.storageprefix + "User");
        }
    }

    get loggedIn() {
        return window.localStorage.getItem(this.storageprefix + "User");
    }

    set expires(val) {
        if (!(val instanceof Date)) {
           val = new Date(val);
        }
        if (val) {
            window.localStorage.setItem(this.storageprefix + "Expires", val);
        } else {
            window.localStorage.removeItem(this.storageprefix + "Expires");
        }
    }

    get expires() {
        let val = window.localStorage.getItem(this.storageprefix + "Expires");
        if (!(val instanceof Date)) {
           val = new Date(val);
        }
        return val
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

        if (response.status === 401 && this.token) {
            // Token has expired. Automatic log out.
            await this.logout();
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
        const token = this.token;
        if (token) {
            allheaders["Authorization"] = `Bearer ${token}`;
        }
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

    async getInfo() {
        return this._fetch({url: `${this.base}/info`});
    }

    async getSchemas({all = false, deletedOnly = false} = {}) {
        const params = new URLSearchParams();
        params.set('all', all);
        params.set('deleted_only', deletedOnly);
        return this._fetch({url: `${this.base}/schema?${params.toString()}`});
    }

    async getSchema({slugOrId} = {}) {
        return this._fetch({url: `${this.base}/schema/${slugOrId}`});
    }

    async createSchema({body} = {}) {
        const response = await this._fetch({
            url: `${this.base}/schema`,
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
            url: `${this.base}/schema/${schemaSlug}`,
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
            url: `${this.base}/schema/${slugOrId}`,
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
        params.set('order_by', orderBy);
        params.set('ascending', ascending);
        for (const [filter, value] of Object.entries(filters)) {
            params.set(filter, value);
        }
        return this._fetch({
            url: `${this.base}/entity/${schemaSlug}?${params.toString()}`
        });
    }

    async getEntity({schemaSlug, entityIdOrSlug} = {}) {
        const params = new URLSearchParams();
        return this._fetch({
            url: `${this.base}/entity/${schemaSlug}/${entityIdOrSlug}?${params.toString()}`
        });
    }

    async createEntity({schemaSlug, body} = {}) {
        const response = await this._fetch({
            url: `${this.base}/entity/${schemaSlug}`,
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
            url: `${this.base}/entity/${schemaSlug}/${entityIdOrSlug}`,
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
            url: `${this.base}/entity/${schemaSlug}/${entityIdOrSlug}`,
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
        if (response !== null) {
            this.loggedIn = username;
            this.token = response.access_token;
            this.expires = response.expiration_date;
            this.alerts.push("success", `Welcome back, ${username}.`);
        }
        return response;
    }

    async logout() {
        this.token = null;
        this.loggedIn = null;
        this.expires = null;
    }

    async getUsers() {
        return await this._fetch({url: `${this.base}/users`});
    }

    async getUserMemberships({username}) {
        return await this._fetch({
            url: `${this.base}/users/${username}/memberships`
        }) ;
    }

    async activate_user({username}) {
        const response = await this._fetch({
            url: `${this.base}/users/${username}`,
            method: "PATCH"
        });
        if (response !== null) {
            this.alerts.push("success", `User activated: ${username}`);
        }
        return response
    }

    async deactivate_user({username}) {
        const response = await this._fetch({
            url: `${this.base}/users/${username}`,
            method: "DELETE"
        });
        if (response !== null) {
            this.alerts.push("success", `User deactivated: ${username}`);
        }
        return response
    }

    async getGroups() {
        return await this._fetch({url: `${this.base}/groups`});
    }

    async getMembers({groupId}) {
        return await this._fetch({url: `${this.base}/groups/${groupId}/members`});
    }

    async createGroup({body}) {
        const response = await this._fetch({
            url: `${this.base}/groups`,
            body: body,
            method: "POST"
        });
        if (response !== null) {
            this.alerts.push("success", `Created new group: ${response.name}`);
        }
        return response;
    }

    async updateGroup({groupId, body}) {
        const response = await this._fetch({
          url:  `${this.base}/groups/${groupId}`,
          body: body,
          method: "PUT"
        });
        if (response !== null) {
          this.alerts.push("success", `Changes to group have been saved: ${body.name}`)
        }
        return response;
    }

    async deleteGroup({groupId}) {
        const response = await this._fetch({
            url: `${this.base}/groups/${groupId}`,
            method: 'DELETE'
        });
        if (response !== null) {
            this.alerts.push("success", "Group has been deleted");
        }
        return response;
    }

    async addMembers({groupId, userIds}) {
        const response = await this._fetch({
            url: `${this.base}/groups/${groupId}/members`,
            body: userIds,
            method: "PATCH"
        });
        if (response !== null) {
            if (response) {
                this.alerts.push("success", "New members were added to group.");
            } else {
                this.alerts.push("warning", "No new members added to group because requested users are already members.");
            }
        }
        return response;
    }

    async removeMembers({groupId, userIds}) {
        const response = await this._fetch({
            url: `${this.base}/groups/${groupId}/members`,
            body: userIds,
            method: "DELETE"
        });
        if (response !== null) {
            if (response) {
                this.alerts.push("success", "Members were removed from group.");
            } else {
                this.alerts.push("warning", "No members were removed from group because requested users were no members.");
            }
        }
        return response;
    }

    async getPermissions({recipientType=null, recipientId=null, objType=null, objId=null}) {
        const params = new URLSearchParams();
        if (recipientId) {
            params.set("recipient_id", recipientId);
        }
        if (recipientType) {
            params.set("recipient_type", recipientType);
        }
        if (objType) {
            params.set("obj_type", objType);
        }
        if (objId) {
            params.set("obj_id", objId);
        }
        return await this._fetch({url: `${this.base}/permissions?${params.toString()}`});
    }

    async grantPermission({recipientType, recipientName, objType, objId, permission}) {
        const response = await this._fetch({
            url: `${this.base}/permissions`,
            method: 'POST',
            body: {
                recipient_type: recipientType,
                recipient_name: recipientName,
                obj_type: objType,
                obj_id: objId,
                permission: permission
            }
        })
        if (response) {
            this.alerts.push("success", "Permission granted.")
        } else {
            this.alerts.push("warning", "Granting of permission not possible.")
        }
    }

    async revokePermissions({permissionIds}) {
        const response = this._fetch({
            url: `${this.base}/permissions`,
            body: permissionIds,
            method: 'DELETE'
        });
        if (response != null) {
            this.alerts.push("success", "Selected permissions revoked.");
        } else {
            this.alerts.push("warning", "Not able to revoke selected permissions.");
        }
        return response;
    }
}


export default {
    install: (app) => {
        app.config.globalProperties.$api = reactive(new API(app));
    }
}