from typing import List, Optional

from fastapi import FastAPI
from fastapi._compat import GenerateJsonSchema, get_compat_model_name_map, get_definitions
from fastapi.openapi.constants import REF_TEMPLATE
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_fields_from_routes, get_openapi, get_openapi_path
from sqlalchemy import select
from sqlalchemy.orm import Session, subqueryload

from .config import settings, VERSION
from .database import SessionLocal
from .enum import FilterEnum
from .dynamic_routes import create_dynamic_router, router as dynamic_router
from .models import Schema, AttributeDefinition, AttrType
from .general_routes import router


def load_schemas(db: Session) -> List[models.Schema]:
    schemas = db.execute(
        select(Schema)
        .options(
            subqueryload(Schema.attr_defs)
        )
    ).scalars().all()
    return schemas


def generate_api_description() -> str:
    description = '# Filters\n\n**Filters list**:'
    for filter in FilterEnum:
        description += '\n* `{}` - {}'.format(filter.value.name, filter.value.description)

    description += '\n\n**Available filters for each type**:'
    for atype in AttrType:
        description += '\n* `{}`: {}'.format(atype.name, ', '.join([f'`{i.value.name}`' for i in atype.value.filters]))
    return description


def load_dynamic_routes(db: Session, app: FastAPI):
    schemas = load_schemas(db)
    for schema in schemas:
        create_dynamic_router(schema=schema, app=app)


def fix_openapi_schema(db, app):
    openapi_schema = get_openapi(
        title='AIMAAS–API',
        summary='Application Programming Interface for the '
                'Abstract Information Management and Authority Service.',
        version=VERSION,
        description=generate_api_description(),
        routes=app.routes,
    )
    ### BEGIN_TODO: remove & rework this whole section

    # First, remove the existing paths under /entity...
    paths_to_remove = [path for path in openapi_schema['paths'].keys() if path.startswith('/entity')]
    for path in paths_to_remove:
        openapi_schema['paths'].pop(path)
    # Now do what `get_openapi` usually does, so we can understand it...

    # Get all ModelFields from routes in a flat list.
    all_fields = get_fields_from_routes(app.routes)
    # Create mapping between required enum/model classes and schema names
    model_name_map = get_compat_model_name_map(all_fields)
    # This "schema generator" is just a dataclass that only holds a single attribute
    # and the value is just a short string template: "#/components/schemas/{model}".
    schema_generator = GenerateJsonSchema(ref_template=REF_TEMPLATE)
    # Create:
    # * a supposed "field mapping", which is *always* an empty dict (at least with pydantic v1)
    # + a dict of model schema definitions, created by:
    #   - first getting a flat set of all the models and sub-models for all the fields,
    #   - then going through those models and, for each, generating its schema, schema definitions of submodels and nested models
    #   - collecting all those schema definitions in one dict with the model name (str) as key.
    field_mapping, model_definitions = get_definitions(
        fields=all_fields,
        schema_generator=schema_generator,
        model_name_map=model_name_map,
    )
    from pprint import pprint; import pdb; pdb.set_trace()  # TODO: remove
    # After these prelims, recreate the routes the same way `get_openapi`normally does:
    operation_ids = set()
    for route in app.routes:
        if route.path in paths_to_remove:
            # Create OpenAPI path for route by doing the following:
            # * check if `route.include_in_schema` is `True`, otherwise path is just an ampty dict
            # * Iterate over `route.methods` (asserted to be a list earlier) and for each method
            #   - call `get_openapi_operation_metadata` with the route, method and operation_ids to get operation metadata
            #   - call `...` ... you know what? `get_openapi_path is an incredibly, stupidly, mind-boggingly long function that does way to mayn things and I don't think writing that all down here will get me anywhere.
            result = get_openapi_path(
                route=route,
                operation_ids=operation_ids,
                schema_generator=schema_generator,
                model_name_map=model_name_map,
                field_mapping=field_mapping,
                separate_input_output_schemas=True,
            )
            if result:
                path, _, _ = result
                if path:
                    openapi_schema['paths'].setdefault(route.path_format, {}).update(path)
    ### END_TODO

    # Earlier experiment:
    # Here we go through the schemas and create dummy entries for them...
    # schemas = load_schemas(db)
    # for schema in schemas:
    #     openapi_schema['paths'][f'/entity/{schema.slug}'] = {
    #         'get': {
    #             'description': 'foo',
    #             'tags': {
    #                 0: schema.name,
    #             },
    #             'responses': {
    #                 200: {
    #                     'description': 'foobar',
    #                     'content': {
    #                         'application/json': {
    #                             'schema': {
    #                                 'type': 'array'
    #                             },
    #                         },
    #                     },
    #                 },
    #             },
    #         },
    #     }
    return openapi_schema


def create_app(session: Optional[Session] = None) -> FastAPI:
    app = FastAPI()
    origins = ['*']
    app.add_middleware(CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'])

    if session:
        load_dynamic_routes(db=session, app=app)
    else:
        with SessionLocal() as db:
            load_dynamic_routes(db=db, app=app)

    app.include_router(router)
    app.include_router(dynamic_router)

    # Need to use a closure here to be able to pass `app` to `fix_openapi_schema`
    # def get_custom_openapi():
    #     return fix_openapi_schema(db, app)
    # app.openapi = get_custom_openapi

    return app
