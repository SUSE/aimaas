export function formatDate(date) {
    return new Date(date).toLocaleString();
}


export function titleCase(string) {
    return string[0].toUpperCase() + string.slice(1).toLowerCase();
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

export const OPERATOR_DESCRIPTION_MAP = {
    eq: "equals to",
    ne: "not equal to",
    lt: "less than",
    le: "less than or equal to",
    gt: "greater than",
    ge: "greater than or equal",
    contains: "contains substring",
    regexp: "matches regular expression",
    starts: "starts with substring",
};


export const CHANGE_STATUS_MAP = {
    PENDING: 'light',
    DECLINED: 'warning',
    APPROVED: 'success',
    add: 'add',
    delete: 'remove',
    update: 'mode_edit'
}
