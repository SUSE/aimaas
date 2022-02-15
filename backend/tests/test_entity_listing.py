from random import choice
import random

from ..config import *
from ..crud import *
from ..models import *
from ..schemas import *
from ..exceptions import *

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

    # test 1
    ## ascending
    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field'
    ).entities
    assert [i['id'] for i in result] == [i['id'] for i in entities]

    ### pagination 10, 0
    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        limit=10,
        offset=0
    ).entities
    assert [i['id'] for i in result] == [i['id'] for i in entities][0:10]

    ### pagination 10, 20
    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        limit=10,
        offset=20
    ).entities
    assert [i['id'] for i in result] == [i['id'] for i in entities][20:30]
    
    ## descenging
    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        ascending=False
    ).entities
    assert [i['id'] for i in result] == [i['id'] for i in entities][::-1]


    # test 2
    ## ascending
    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        filters={'name.contains': 'j'}
    ).entities
    filtered = [i for i in entities if 'j' in i['name']]
    a = 5
    assert [i['id'] for i in result] == [i['id'] for i in filtered]
    
    ## descending
    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        filters={'name.contains': 'j'},
        ascending=False
    ).entities
    filtered = [i for i in entities if 'j' in i['name']][::-1]
    assert [i['id'] for i in result] == [i['id'] for i in filtered]

    # test 3
    ## ascending
    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        filters={'name.contains': 'j', 'string_field.starts': 'a'}
    ).entities
    filtered = [i for i in entities if 'j' in i['name'] and i['string_field'].startswith('a')]
    assert [i['id'] for i in result] == [i['id'] for i in filtered]

    ## descending
    result = get_entities(
        db=dbsession, 
        schema=schema, 
        all_fields=True, 
        order_by='int_field',
        filters={'name.contains': 'j', 'string_field.starts': 'a'},
        ascending=False
    ).entities
    filtered = [i for i in entities if 'j' in i['name'] and i['string_field'].startswith('a')][::-1]
    assert [i['id'] for i in result] == [i['id'] for i in filtered]

    # test 4
    ## ascending
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
    ).entities
    filtered = [i for i in entities if 'j' in i['name'] 
                and i['string_field'].startswith('a') 
                and i['int_field'] > 50
                and i['int_field'] < 550]
    assert [i['id'] for i in result] == [i['id'] for i in filtered]

    ## descending
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
    ).entities
    filtered = [i for i in entities if 'j' in i['name'] 
                and i['string_field'].startswith('a') 
                and i['int_field'] > 50
                and i['int_field'] < 550][::-1]
    assert [i['id'] for i in result] == [i['id'] for i in filtered]