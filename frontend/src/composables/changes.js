export async function loadChangeDetails(api, objectType, changeId, targetObject, transformCallback) {
    if (changeId in targetObject) {
        return;
    }
    const details = await api.getChangeRequestDetails({
        objectType: objectType,
        changeId: changeId
    });
    if (transformCallback) {
        targetObject[changeId] = await transformCallback(details);
    } else {
        targetObject[changeId] = details;
    }
}


const fixed_headers = ['action', 'name', 'new_name', 'slug', 'new', 'old', 'current'];


export function sortChangeHeaders(x, y) {
    const xif = fixed_headers.includes(x);
    const yif = fixed_headers.includes(y);
    if (xif && yif) {
        if (fixed_headers.indexOf(x) < fixed_headers.indexOf(y)) {
            return -1;
        }
        return 1;
    } else if (!xif && !yif) {
        // Both values are a fixed header or none are
        if (x < y) {
            return -1;
        } else {
            return 1;
        }
    } else if (xif) {
        // Only xif is a fixed header
        return -1;
    }
    // Only yif is a fixed header
    return 1;
}