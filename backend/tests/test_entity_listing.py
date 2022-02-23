from random import choice
import random

from fastapi_pagination import Params

from ..config import DEFAULT_PARAMS
from ..crud import *
from ..models import *
from ..schemas import *

from copy import copy


def data_for_test(db: Session, count: int):
    random.seed(42)
    schema = create_schema(db=db, data=SchemaCreateSchema(
        name='test', slug='test', attributes=[
            AttrDefSchema(
                name='int_field',
                type='INT',
                required=False,
                unique=False,
                list=False,
                key=False
            ),
            AttrDefSchema(
                name='string_field',
                type='STR',
                required=False,
                unique=False,
                list=False,
                key=False
            )
        ]
    ))
    entities = []
    names = [
        'john', 'jane', 'jim', 
        'mike', 'miles', 'monty',
        'nick', 'nicolas', 'nelson',
        'dave', 'david', 'dan' 
        'alan', 'alyx', 'alice']
    for i in range(count):
        entities.append(
            {
                'name': f'{choice(names)}_{i}',
                'slug': f'{choice(names)}_{i}',
                'int_field': i,
                'string_field': f'{choice(names)}'
            }
        )
    for e in entities:

        ent = create_entity(db=db, schema_id=schema.id, data=copy(e))
        e['id'] = ent.id

    return entities, schema


def test_stuff(dbsession):
    entities, schema = data_for_test(dbsession, 1000)

    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field'
    ).items
    assert [i['id'] for i in result] == [i['id'] for i in entities[:DEFAULT_PARAMS.size]]

    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        params=Params(size=20, page=1)
    ).items
    assert [i['id'] for i in result] == [i['id'] for i in entities][0:20]

    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        params=Params(size=10, page=2)
    ).items
    assert [i['id'] for i in result] == [i['id'] for i in entities][10:20]

    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        ascending=False
    ).items
    assert [i['id'] for i in result] == [i['id'] for i in entities[-DEFAULT_PARAMS.size:][::-1]]

    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        filters={'name.contains': 'j'}
    ).items
    assert all("j" in i["name"] for i in result)
    filtered = [i for i in entities if 'j' in i['name']][:DEFAULT_PARAMS.size]
    assert [i['id'] for i in result] == [i['id'] for i in filtered]
    
    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        filters={'name.contains': 'j'},
        ascending=False
    ).items
    filtered = [i for i in entities if 'j' in i['name']][::-1][:DEFAULT_PARAMS.size]
    assert [i['id'] for i in result] == [i['id'] for i in filtered]

    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        filters={'name.contains': 'j', 'string_field.starts': 'a'}
    ).items
    filtered = [i for i in entities
                if 'j' in i['name'] and i['string_field'].startswith('a')][:DEFAULT_PARAMS.size]
    assert [i['id'] for i in result] == [i['id'] for i in filtered]

    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        filters={'name.contains': 'j', 'string_field.starts': 'a'},
        ascending=False
    ).items
    filtered = [i for i in entities
                if 'j' in i['name'] and i['string_field'].startswith('a')][::-1][:DEFAULT_PARAMS.size]
    assert [i['id'] for i in result] == [i['id'] for i in filtered]

    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        filters={
            'name.contains': 'j', 
            'string_field.starts': 'a', 
            'int_field.gt': 50,
            'int_field.lt': 550
        }
    ).items
    filtered = [i for i in entities
                if 'j' in i['name']
                and i['string_field'].startswith('a') 
                and i['int_field'] > 50
                and i['int_field'] < 550][:DEFAULT_PARAMS.size]
    assert [i['id'] for i in result] == [i['id'] for i in filtered]

    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        filters={
            'name.contains': 'j', 
            'string_field.starts': 'a', 
            'int_field.gt': 50,
            'int_field.lt': 550
        },
        ascending=False
    ).items
    filtered = [i for i in entities
                if 'j' in i['name']
                and i['string_field'].startswith('a') 
                and i['int_field'] > 50
                and i['int_field'] < 550][::-1][:DEFAULT_PARAMS.size]
    assert [i['id'] for i in result] == [i['id'] for i in filtered]
