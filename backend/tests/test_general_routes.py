from typing import List

from sqlalchemy import update

from ..models import *


class TestRouteAttributes:
    def test_get_attributes(self, dbsession, client):
        attrs = [
            {'id': 1, 'name': 'age', 'type': 'FLOAT'},
            {'id': 2, 'name': 'age', 'type': 'INT'},
            {'id': 3, 'name': 'age', 'type': 'STR'},
            {'id': 4, 'name': 'born', 'type': 'DT'},
            {'id': 5, 'name': 'friends', 'type': 'FK'},
            {'id': 6, 'name': 'address', 'type': 'FK'},
            {'id': 7, 'name': 'nickname', 'type': 'STR'}
        ]
        response = client.get('/attributes')
        assert response.json() == attrs

    def test_get_attribute(self, dbsession, client):
        response = client.get('/attributes/1')
        assert response.json() == {'id': 1, 'name': 'age', 'type': 'FLOAT'}

    def test_raise_on_attribute_doesnt_exist(self, dbsession, client):
        response = client.get('/attributes/123456789')
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

class TestRouteSchemasGet:
    def test_get_schemas(self, dbsession, client):
        test = Schema(name='Test', slug='test', deleted=True)
        dbsession.add(test)
        dbsession.commit()

        response = client.get('/schemas')
        assert response.status_code == 200
        assert response.json() == [{'id': 1, 'name': 'Person', 'slug': 'person'}]

    def test_get_all(self, dbsession, client):
        test = Schema(name='Test', slug='test', deleted=True)
        dbsession.add(test)
        dbsession.commit()

        response = client.get('/schemas?all=True')
        assert response.status_code == 200
        assert response.json() == [{'id': 1, 'name': 'Person', 'slug': 'person'}, {'id': 2, 'name': 'Test', 'slug': 'test'}]

        response = client.get('/schemas?all=True&deleted_only=True')
        assert response.status_code == 200
        assert response.json() == [{'id': 1, 'name': 'Person', 'slug': 'person'}, {'id': 2, 'name': 'Test', 'slug': 'test'}]

    def test_get_deleted_only(self, dbsession, client):
        test = Schema(name='Test', slug='test', deleted=True)
        dbsession.add(test)
        dbsession.commit()

        response = client.get('/schemas?deleted_only=True')
        assert response.status_code == 200
        assert response.json() == [{'id': 2, 'name': 'Test', 'slug': 'test'}]

    def test_get_schema(self, dbsession, client):
        schema = {
            'attributes': [
                {'bind_to_schema': None,
                 'description': 'Age of this person',
                 'key': True,
                 'list': False,
                 'name': 'age',
                 'required': True,
                 'type': 'INT',
                 'unique': False
                },
                {'bind_to_schema': None,
                 'description': None,
                 'key': False,
                 'list': False,
                 'name': 'born',
                 'required': False,
                 'type': 'DT',
                 'unique': False
                },
                {'bind_to_schema': None,
                 'description': None,
                 'key': False,
                 'list': True,
                 'name': 'friends',
                 'required': True,
                 'type': 'FK',
                 'unique': False
                },
                {'bind_to_schema': None,
                 'description': None,
                 'key': False,
                 'list': False,
                 'name': 'nickname',
                 'required': False,
                 'type': 'STR',
                 'unique': True
                 }
            ],
            'deleted': False,
            'id': 1,
            'name': 'Person',
            'slug': 'person'
        }

        response = client.get('/schemas/1')
        assert response.json() == schema

        response = client.get('/schemas/person')
        assert response.json() == schema

    def test_raise_on_schema_doesnt_exist(self, dbsession, client):
        response = client.get('/schemas/12345678')
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

        response = client.get('/schemas/qwertyui')
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

class TestRouteSchemaCreate:
    def attrs(self, db: Session) -> List[Attribute]:
        color = Attribute(name='color', type=AttrType.STR)
        max_speed =  Attribute(name='max_speed', type=AttrType.INT)
        release_year = Attribute(name='release_year', type=AttrType.DT)
        owner = Attribute(name='owner', type=AttrType.FK)

        db.add_all([color, max_speed, release_year, owner])
        db.commit()
        return [color, max_speed, release_year, owner]

    def test_create(self, dbsession, client):
        color, max_speed, release_year, owner = self.attrs(dbsession)
        data = {
            'name': 'Car',
            'slug': 'car',
            'attributes': [
                {
                    'attribute_id': color.id,   # this
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'description': 'Color of this car'
                },
                {
                    'attr_id': max_speed.id,  # and this are the same
                    'required': True,
                    'unique': False,
                    'list': False,
                    'key': False,
                },
                {
                    'attr_id': release_year.id,
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                },
                {
                    'attr_id': owner.id,
                    'required': True,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': 1
                }
            ]
        }
        response = client.post('/schemas', json=data)
        assert response.status_code == 200
        assert response.json() == {'id': 2, 'name': 'Car', 'slug': 'car'}

        car = dbsession.execute(select(Schema).where(Schema.name == 'Car')).scalar()
        assert car is not None and car.id == 2 and car.slug == 'car'

        attr_defs = dbsession.execute(select(AttributeDefinition).where(AttributeDefinition.schema_id == car.id)).scalars().all()
        assert len(attr_defs) == 4

        color_ = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == car.id)
            .where(AttributeDefinition.attribute_id == color.id)
        ).scalar()
        assert not any([color_.required, color_.unique, color_.list, color_.key])
        assert color_.description == 'Color of this car'

        ry = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == car.id)
            .where(AttributeDefinition.attribute_id == release_year.id)
        ).scalar()
        assert not any([ry.required, ry.unique, ry.list, ry.key])
        assert ry.description is None

        owner_ = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == car.id)
            .where(AttributeDefinition.attribute_id == owner.id)
        ).scalar()
        bfk = dbsession.execute(select(BoundFK).where(BoundFK.attr_def_id == owner_.id)).scalars().all()
        assert len(bfk) == 1 and bfk[0].schema.name == 'Person'

    def test_create_with_attr_data(self, dbsession, client):
        color, *_ = self.attrs(dbsession)
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'name': 'test1',
                    'type': 'STR',
                    'required': True,
                    'unique': True,
                    'list': False,
                    'key': True,
                    'description': 'Test 1'
                },
                {
                    'name': 'test2',
                    'type': 'STR',
                    'required': True,
                    'unique': True,
                    'list': False,
                    'key': True,
                    'description': 'Test 2'
                },
                {
                    'attribute_id': color.id,
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'description': 'Color of this car'
                }
            ]
        }

        response = client.post('/schemas', json=data)
        assert response.status_code == 200
        assert response.json() == {'id': 2, 'name': 'Test', 'slug': 'test'}

        schemas = dbsession.execute(select(Schema)).scalars().all()
        assert len(schemas) == 2

        schema = dbsession.execute(select(Schema).where(Schema.name == 'Test')).scalar()
        assert schema is not None
        
        attr = dbsession.execute(select(Attribute).where(Attribute.name == 'test1')).scalar()
        assert attr is not None

        attr2 = dbsession.execute(select(Attribute).where(Attribute.name == 'test2')).scalar()
        assert attr2 is not None

        attr_defs = dbsession.execute(
            select(AttributeDefinition).where(AttributeDefinition.schema_id == schema.id)
        ).scalars().all()
        assert len(attr_defs) == 3

        attr_def = attr_defs[0]
        assert attr_def is not None
        assert attr_def.attribute == attr
        assert all([attr_def.required, attr_def.unique, attr_def.key])
        assert not attr_def.list
        assert attr_def.description == 'Test 1'

    def test_raise_on_duplicate_name_or_slug(self, dbsession, client):
        data = {
            'name': 'Person',
            'slug': 'test',
            'attributes': []
        }
        response = client.post('/schemas', json=data)
        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']

        data = {
            'name': 'Test',
            'slug': 'person',
            'attributes': []
        }
        response = client.post('/schemas', json=data)
        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']

    def test_raise_on_nonexistent_attr_id(self, dbsession, client):
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'attribute_id': 123456789,
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'description': 'Nonexistent attribute'
                }
            ]
        }
        response = client.post('/schemas', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_empty_schema_when_binding(self, dbsession, client):
        *_, owner = self.attrs(dbsession)
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'attribute_id': owner.id,
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        } 
        response = client.post('/schemas', json=data)
        assert response.status_code == 422
        assert "You must bind attribute" in response.json()['detail']

    def test_raise_on_nonexistent_schema_when_binding(self, dbsession, client):
        *_, owner = self.attrs(dbsession)
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'attribute_id': owner.id,
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': 123456789
                }
            ]
        } 
        response = client.post('/schemas', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_passed_deleted_schema_for_binding(self, dbsession, client):
        dbsession.execute(update(Schema).where(Schema.id == 1).values(deleted=True))
        dbsession.commit()
        *_, owner = self.attrs(dbsession)
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'attribute_id': owner.id,
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': 1
                }
            ]
        } 
        response = client.post('/schemas', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_multiple_attrs_with_same_name(self, dbsession, client):
        color, *_ = self.attrs(dbsession)
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'name': 'test1',
                    'type': 'STR',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                },
                {
                    'name': 'test1',
                    'type': 'INT',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        } 
        response = client.post('/schemas', json=data)
        assert response.status_code == 409
        assert "Found multiple occurrences of attribute" in response.json()['detail']

        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'name': 'color',
                    'type': 'INT',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                },
                {
                    'attr_id': color.id,
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        } 
        response = client.post('/schemas', json=data)
        assert response.status_code == 409
        assert "Found multiple occurrences of attribute" in response.json()['detail']

        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'attr_id': color.id,
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                },
                {
                    'attr_id': color.id,
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        } 
        response = client.post('/schemas', json=data)
        assert response.status_code == 409
        assert "Found multiple occurrences of attribute" in response.json()['detail']


class TestRouteSchemaUpdate:
    def test_update(self, dbsession, client):
        address = dbsession.execute(select(Attribute).where(Attribute.name == 'address')).scalar()
        age = dbsession.execute(
            select(AttributeDefinition)
            .join(Attribute)
            .where(Attribute.name == 'age')
            .where(AttributeDefinition.schema_id == 1)
        ).scalar()

        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [
                {
                    'attr_def_id': age.id,
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'description': 'Age of this person'
                }
            ],
            'add_attributes': [
                {
                    'attribute_id': address.id,
                    'required': True,
                    'unique': True,
                    'list': True,
                    'key': True,
                    'bind_to_schema': -1
                }
            ]
        } 
        result = {
            'attributes': [
                {
                    'bind_to_schema': None,
                    'description': 'Age of this person',
                    'key': False,
                    'list': False,
                    'name': 'age',
                    'required': False,
                    'type': 'INT',
                    'unique': False
                },
                {
                    'bind_to_schema': None,
                    'description': None,
                    'key': False,
                    'list': False,
                    'name': 'born',
                    'required': False,
                    'type': 'DT',
                    'unique': False
                },
                {
                    'bind_to_schema': None,
                    'description': None,
                    'key': False,
                    'list': True,
                    'name': 'friends',
                    'required': True,
                    'type': 'FK',
                    'unique': False
                },
                {
                    'bind_to_schema': None,
                    'description': None,
                    'key': False,
                    'list': False,
                    'name': 'nickname',
                    'required': False,
                    'type': 'STR',
                    'unique': True
                },
                {
                    'bind_to_schema': None,
                    'description': None,
                    'key': True,
                    'list': True,
                    'name': 'address',
                    'required': True,
                    'type': 'FK',
                    'unique': False
                }
            ],
            'deleted': False,
            'id': 1,
            'name': 'Test',
            'slug': 'test'
        }

        response = client.put('/schemas/1', json=data)
        assert response.status_code == 200
        assert response.json() == result

        dbsession.expire_all()
        age_def = dbsession.execute(
            select(AttributeDefinition)
            .join(Attribute)
            .where(Attribute.name == 'age')
            .where(AttributeDefinition.schema_id == 1)
        ).scalar()
        assert age_def is not None
        assert not any([age_def.required, age_def.unique, age_def.list, age_def.key])

        address_def = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.attribute_id == address.id)
            .where(AttributeDefinition.schema_id == 1)
        ).scalar()
        assert address_def is not None
        assert all([address_def.list, address_def.key, address_def.required])
        assert not address_def.unique

        bfk = dbsession.execute(
            select(BoundFK)
            .where(BoundFK.schema_id == 1)
            .where(BoundFK.attr_def_id == address_def.id)
        ).scalar()
        assert bfk is not None

        sch = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        assert sch.name == 'Test' and sch.slug == 'test'

    def test_update_attr_def_with_name(self, dbsession, client):
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [
                {
                    'name': 'age',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'description': 'Age of this person'
                }
            ],
            'add_attributes': []
        } 
        result = {
            'attributes': [
                {
                    'bind_to_schema': None,
                    'description': 'Age of this person',
                    'key': False,
                    'list': False,
                    'name': 'age',
                    'required': False,
                    'type': 'INT',
                    'unique': False
                },
                {
                    'bind_to_schema': None,
                    'description': None,
                    'key': False,
                    'list': False,
                    'name': 'born',
                    'required': False,
                    'type': 'DT',
                    'unique': False},
                {
                    'bind_to_schema': None,
                    'description': None,
                    'key': False,
                    'list': True,
                    'name': 'friends',
                    'required': True,
                    'type': 'FK',
                    'unique': False
                },
                {
                    'bind_to_schema': None,
                    'description': None,
                    'key': False,
                    'list': False,
                    'name': 'nickname',
                    'required': False,
                    'type': 'STR',
                    'unique': True
                }
            ],
            'deleted': False,
            'id': 1,
            'name': 'Test',
            'slug': 'test'
        }

        response = client.put('/schemas/1', json=data)
        assert response.status_code == 200
        assert response.json() == result


        age_def = dbsession.execute(
            select(AttributeDefinition)
            .join(Attribute)
            .where(Attribute.name == 'age')
            .where(AttributeDefinition.schema_id == 1)
        ).scalar()
        assert age_def is not None
        assert not any([age_def.required, age_def.unique, age_def.list, age_def.key])

    def test_update_with_attr_data(self, dbsession, client):
        address = dbsession.execute(select(Attribute).where(Attribute.name == 'address')).scalar()
        age = dbsession.execute(
            select(AttributeDefinition)
            .join(Attribute)
            .where(Attribute.name == 'age')
            .where(AttributeDefinition.schema_id == 1)
        ).scalar()
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [
                {
                    'attr_def_id': age.id,
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'description': 'Age of this person'
                }
            ],
            'add_attributes': [
                {
                    'attribute_id': address.id,
                    'required': True,
                    'unique': True,
                    'list': True,
                    'key': True,
                    'bind_to_schema': -1
                },
                {
                    'name': 'test',
                    'type': 'FK',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'description': 'test',
                    'bind_to_schema': -1
                }
            ]
        } 
        result = {
            'attributes': [
                {
                    'bind_to_schema': None,
                    'description': 'Age of this person',
                    'key': False,
                    'list': False,
                    'name': 'age',
                    'required': False,
                    'type': 'INT',
                    'unique': False
                },
                {
                    'bind_to_schema': None,
                    'description': None,
                    'key': False,
                    'list': False,
                    'name': 'born',
                    'required': False,
                    'type': 'DT',
                    'unique': False
                },
                {
                    'bind_to_schema': None,
                    'description': None,
                    'key': False,
                    'list': True,
                    'name': 'friends',
                    'required': True,
                    'type': 'FK',
                    'unique': False
                },
                {
                    'bind_to_schema': None,
                    'description': None,
                    'key': False,
                    'list': False,
                    'name': 'nickname',
                    'required': False,
                    'type': 'STR',
                    'unique': True
                },
                {
                    'bind_to_schema': None,
                    'description': None,
                    'key': True,
                    'list': True,
                    'name': 'address',
                    'required': True,
                    'type': 'FK',
                    'unique': False
                },
                {
                        'bind_to_schema': None,
                    'description': 'test',
                    'key': False,
                    'list': False,
                    'name': 'test',
                    'required': False,
                    'type': 'FK',
                    'unique': False
                }
            ],
            'deleted': False,
            'id': 1,
            'name': 'Test',
            'slug': 'test'
        }

        response = client.put('/schemas/1', json=data)
        assert response.status_code == 200
        assert response.json() == result

        dbsession.expire_all()
        address_def = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.attribute_id == address.id)
            .where(AttributeDefinition.schema_id == 1)
        ).scalar()
        assert address_def is not None
        assert not address_def.unique and address_def.list
        age_def = dbsession.execute(
            select(AttributeDefinition)
            .join(Attribute)
            .where(Attribute.name == 'age')
            .where(AttributeDefinition.schema_id == 1)
        ).scalar()
        assert age_def is not None
        assert not any([age_def.required, age_def.unique, age_def.list, age_def.key])
        
        sch = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        assert sch.name == 'Test' and sch.slug == 'test'

        test_def = dbsession.execute(
            select(AttributeDefinition)
            .join(Attribute)
            .where(Attribute.name == 'test')
            .where(AttributeDefinition.schema_id == 1)
        ).scalar()
        assert test_def is not None
        assert test_def.attribute.type == AttrType.FK
        bfk = dbsession.execute(
            select(BoundFK)
            .where(BoundFK.schema_id == 1)
            .where(BoundFK.attr_def_id == test_def.id)
        ).scalar()
        assert bfk


    def test_raise_on_schema_doesnt_exist(self, dbsession, client):
        data = {
            'name': 'Test',
            'slug': 'person',
            'update_attributes': [],
            'add_attributes': []
        }
        response = client.put('/schemas/12345678', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_existing_slug_or_name(self, dbsession, client):
        new_sch = Schema(name='Test', slug='test')
        dbsession.add(new_sch)
        dbsession.commit()
        
        data = {
            'name': 'Test',
            'slug': 'person',
            'update_attributes': [],
            'add_attributes': []
        }
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']

        ata = {
            'name': 'Person',
            'slug': 'test',
            'update_attributes': [],
            'add_attributes': []
        }
        response = client.put('/schemas/person', json=data)
        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']

    def test_raise_on_attr_def_doesnt_exist(self, dbsession, client):
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [
                {
                    'attr_def_id': 12345678,
                    'required': True,
                    'unique': True,
                    'list': False,
                    'key': True
                }
            ],
            'add_attributes': []
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 404
        assert "is not defined on schema" in response.json()['detail']

    def test_raise_on_convert_list_to_single(self, dbsession, client):
        attr_def = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == 1)
            .join(Attribute)
            .where(Attribute.name == 'friends')
        ).scalar()
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [
                {
                    'attr_def_id': attr_def.id,
                    'required': True,
                    'unique': True,
                    'list': False,
                    'key': True
                }
            ],
            'add_attributes': []
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 409
        assert "is listed, can't make unlisted" in response.json()['detail']

    def test_raise_on_attr_doesnt_exist(self, dbsession, client):
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [],
            'add_attributes': [
                {
                    'attr_id': 12345678,
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']
    
    def test_raise_on_attr_def_already_exists(self, dbsession, client):
        attr = dbsession.execute(select(Attribute).where(Attribute.name == 'born')).scalar()
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [],
            'add_attributes': [
                {
                    'attr_id': attr.id,
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 409
        assert "already defined" in response.json()['detail']

        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [],
            'add_attributes': [
                {
                    'name': 'born',
                    'type': 'STR',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 409
        assert "already defined" in response.json()['detail']


    def test_raise_on_nonexistent_schema_when_binding(self, dbsession, client):
        attr = dbsession.execute(
            select(Attribute)
            .where(Attribute.name == 'address')
        ).scalar()
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [],
            'add_attributes': [
                {
                    'attr_id': attr.id,
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': 123456789
                }
            ]
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_schema_not_passed_when_binding(self, dbsession, client):
        attr = dbsession.execute(
            select(Attribute)
            .where(Attribute.name == 'address')
        ).scalar()
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [],
            'add_attributes': [
                {
                    'attr_id': attr.id,
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 422
        assert "You must bind attribute" in response.json()['detail']

    def test_raise_on_multiple_attrs_with_same_name(self, dbsession, client):
        address = dbsession.execute(
            select(Attribute)
            .where(Attribute.name == 'address')
        ).scalar()
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [],
            'add_attributes': [
                {
                    'attr_id': address.id,
                    'type': 'STR',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': -1
                },
                {
                    'attribute_id': address.id,
                    'type': 'INT',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': -1
                }
            ]
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 409
        assert "Found multiple occurrences of attribute" in response.json()['detail']

        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [],
            'add_attributes': [
                {
                    'name': 'address',
                    'type': 'DT',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                },
                {
                    'attr_id': address.id,
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': -1
                }
            ]
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 409
        assert "Found multiple occurrences of attribute" in response.json()['detail']