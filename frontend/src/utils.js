

export function titleCase(string){
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

const FIELD_TYPE_COMPONENT = {
    DT: 'ValueDateTime',
    BOOL: 'ValueBool',
    FK: 'ValueReference',
}


export function getFieldsInfo(fieldsMeta){
    const res = {};
    for (const [attr, props] of Object.entries(fieldsMeta)){
        const component = FIELD_TYPE_COMPONENT[props.type] || 'ValueString';
        res[attr] = {component, type: props.type, list: props.list, bind_to_schema: props.bind_to_schema}
    }
    return res;
}