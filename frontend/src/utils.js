function dec2hex(dec) {
    return dec.toString(16).padStart(2, "0")
}


export function randomUUID() {
    try {
        return crypto.randomUUID();
    } catch (e) {
        // We don't have this function at our disposal? Use something else :P
        const arr = new Uint8Array(16);
        crypto.getRandomValues(arr);
        return Array.from(arr, dec2hex).join('');
    }
}


export function formatDate(date) {
    if (date instanceof Date) {
        return date.toLocaleString();
    } else {
        return new Date(date).toLocaleString();
    }
}


export const ATTR_TYPES_NAMES = {
    STR: "string",
    BOOL: "boolean",
    INT: "integer",
    FLOAT: "float",
    FK: "reference",
    DT: "datetime",
    DATE: "date",
};


export const TYPE_INPUT_MAP = {
    STR: "TextInput",
    DT: "DateTime",
    INT: "IntegerInput",
    FLOAT: "FloatInput",
    BOOL: "Checkbox",
    DATE: "DateInput",
};


export const CHANGE_STATUS_MAP = {
    PENDING: 'light',
    DECLINED: 'warning',
    APPROVED: 'success',
    add: 'add',
    create: 'add',
    delete: 'delete',
    update: 'mode_edit',
    restore: 'restore_from_trash'
}
