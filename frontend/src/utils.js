

export function titleCase(string){
    return string[0].toUpperCase() + string.slice(1).toLowerCase();
  }



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