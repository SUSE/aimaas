import typing
from datetime import timezone, timedelta, datetime

import pytest
from sqlalchemy.exc import DataError

from ..crud import *
from ..models import *
from ..exceptions import *

from .mixins import DefaultMixin


class TestEntityCreate(DefaultMixin):
    def asserts_after_entities_create(self, db: Session):
        born = datetime(1990, 6, 30, tzinfo=timezone.utc)
        tz_born = datetime(1983, 10, 31, tzinfo=timezone(timedelta(hours=2)))
        jack = self.get_default_entity(db)

        persons = db.execute(select(Entity).where(Entity.schema_id == jack.schema_id)).scalars().all()
        persons = {p.slug: p for p in persons}

        assert len(persons) == 5

        john = persons["John"]
        mike = persons["Mike"]
        pumpkin_jack = persons["pumpkin-jack"]

        assert john.name == 'John'
        assert john.get('nickname', db).value == 'john'
        assert john.get('age', db).value == 10
        assert john.get('born', db).value == born
        assert isinstance(john.get('age', db), ValueInt)
        assert {i.value for i in john.get('friends', db)} == {jack.id, mike.id}
        assert pumpkin_jack.get('born', db).value.astimezone(timezone.utc) == tz_born.astimezone(
            timezone.utc)

    def test_create(self, dbsession):
        born = datetime(1990, 6, 30, tzinfo=timezone.utc)
        tz_born = datetime(1983, 10, 31, tzinfo=timezone(timedelta(hours=2)))
        p0 = self.get_default_entity(dbsession)
        p1 = {
            'name': 'Mike',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [],
        }
        p1 = create_entity(dbsession, schema_id=p0.schema_id, data=p1)
        p2 = {
            'name': 'John',
            'slug': 'John',
            'nickname': 'john',
            'age': 10,
            'friends': [p1.id, p0.id],
            'born': born
        }
        p2 = create_entity(dbsession, schema_id=p0.schema_id, data=p2)

        p3 = {
            'name': 'Pumpkin Jack',
            'slug': 'pumpkin-jack',
            'nickname': 'pumpkin',
            'age': 38,
            'friends': [p1.id, p2.id],
            'born': tz_born
        }
        p3 = create_entity(dbsession, schema_id=p0.schema_id, data=p3)

        self.asserts_after_entities_create(dbsession)
    
    def test_no_raise_with_empty_optional_single_fk_field(self, dbsession):
        schema = self.get_default_schema(dbsession)
        attr = dbsession.execute(select(Attribute).where(Attribute.name == 'address')).scalar()
        attr_def = AttributeDefinition(
            schema_id=schema.id,
            attribute=attr,
            required=False,
            key=False,
            unique=False,
            list=False
        )
        dbsession.add(attr_def)
        dbsession.commit()
        data = {
            'name': 'Mike',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': []
        }
        create_entity(dbsession, schema_id=schema.id, data=data)

    def test_raise_on_non_unique_slug(self, dbsession):
        schema = self.get_default_schema(dbsession)
        p1 = {
            'name': 'Jack',
            'slug': 'Jack', 
            'nickname': 'test',
            'age': 10,
            'friends': []
        }
        with pytest.raises(EntityExistsException):
            create_entity(dbsession, schema_id=schema.id, data=p1)

    def test_no_raise_on_same_slug_in_different_schemas(self, dbsession):
        s = Schema(name='Test', slug='test')
        dbsession.add(s)
        dbsession.flush()

        data = {'slug': 'Jack', 'name': 'Jack'}
        create_entity(dbsession, schema_id=s.id, data=data)

    def test_raise_on_non_unique_field(self, dbsession):
        p1 = {
            'name': 'Jack',
            'slug': 'Jake', 
            'nickname': 'jack',  # <-- already exists in db
            'age': 10,
            'friends': []
        }
        schema = self.get_default_schema(dbsession)
        with pytest.raises(UniqueValueException):
            create_entity(dbsession, schema_id=schema.id, data=p1)

    def test_no_raise_on_non_unique_value_if_it_is_deleted(self, dbsession):
        jacks = dbsession.execute(select(ValueStr).where(ValueStr.value == 'jack')).scalars().all()
        assert len(jacks) == 1

        p0 = self.get_default_entity(dbsession)
        p0.deleted = True
        dbsession.commit()
        p1 = {
            'name': 'Jack',
            'slug': 'Jackie',  
            'nickname': 'jack',  # <-- already exists in db, but for deleted entity
            'age': 10,
            'friends': []
        }
        e = create_entity(dbsession, schema_id=p0.schema_id, data=p1)
        jacks = dbsession.execute(select(ValueStr).where(ValueStr.value == 'jack')).scalars().all()
        assert len(jacks) == 2
        assert [i.entity_id for i in jacks] == [p0.id, e.id]

    def test_raise_on_schema_doesnt_exist(self, dbsession):
        jack = self.get_default_entity(dbsession)
        p = {
            'name': 'somename',
            'slug': 'Some Name',
            'nickname': 'somename',
            'age': 10,
            'friends': [jack.id]
        }
        with pytest.raises(MissingSchemaException):
            create_entity(dbsession, schema_id=99999, data=p)

    def test_raise_on_attr_doesnt_exist(self, dbsession):
        jack = self.get_default_entity(dbsession)
        p = {
            'name': 'somename',
            'slug': 'SomeName',
            'nickname': 'somename',
            'age': 10,
            'friends': [jack.id],
            'nonexistent': True
        }
        with pytest.raises(AttributeNotDefinedException):
            create_entity(dbsession, schema_id=jack.schema_id, data=p)

    def test_raise_on_value_cast(self, dbsession):
        jack = self.get_default_entity(dbsession)
        p = {
            'name': 'somename',
            'slug': 'SomeName',
            'nickname': 'somename',
            'age': 'INVALID VALUE',
            'friends': [jack.id],
        }
        with pytest.raises(ValueError):
            create_entity(dbsession, schema_id=jack.schema_id, data=p)

    def test_raise_on_passed_list_for_single_value_attr(self, dbsession):
        jack = self.get_default_entity(dbsession)
        p = {
            'name': 'somename',
            'slug': 'Somename',
            'nickname': 'somename',
            'age': [1, 2, 3],
            'friends': [jack.id],
        }
        with pytest.raises(NotListedAttributeException):
            create_entity(dbsession, schema_id=jack.schema_id, data=p)

    def test_raise_on_fk_entity_doesnt_exist(self, dbsession):
        p1 = {
            'name': 'mike',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [99999999]
        }
        schema = self.get_default_schema(dbsession)
        with pytest.raises(MissingEntityException):
            create_entity(dbsession, schema_id=schema.id, data=p1)

    def test_raise_on_fk_entity_is_deleted(self, dbsession):
        jack = self.get_default_entity(dbsession)
        jack.deleted = True
        dbsession.commit()
        p1 = {
            'name': 'mike',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [jack.id]
        }
        with pytest.raises(MissingEntityException):
            create_entity(dbsession, schema_id=jack.schema_id, data=p1)

    def test_raise_on_fk_entity_from_wrong_schema(self, dbsession):
        schema = Schema(name='Test', slug='test')
        dbsession.add(schema)
        dbsession.flush()
        entity = Entity(schema_id=schema.id, slug='test', name='test')
        dbsession.add(entity)
        dbsession.flush()

        p1 = {
            'name': 'mike',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [entity.id]
        }
        person = self.get_default_schema(dbsession)
        with pytest.raises(WrongSchemaToBindException):
            create_entity(dbsession, schema_id=person.id, data=p1)

    def test_raise_on_slug_not_provided(self, dbsession):
        jack = self.get_default_entity(dbsession)
        p1 = {
            'nickname': 'mike',
            'age': 10,
            'friends': [jack.id]
        }
        with pytest.raises(RequiredFieldException):
            create_entity(dbsession, schema_id=jack.schema_id, data=p1)

    def test_raise_on_required_field_not_provided(self, dbsession):
        jack = self.get_default_entity(dbsession)
        p1 = {
            'slug': 'Mike',
            'name': 'mike',
            'friends': [jack.id]
        }
        with pytest.raises(RequiredFieldException):
            create_entity(dbsession, schema_id=jack.schema_id, data=p1)

    def test_raise_on_value_out_of_range(self, dbsession):
        schema = self.get_default_schema(dbsession)
        with pytest.raises(DataError):
            create_entity(dbsession, schema_id=schema.id, data={"name": "Frank", "slug": "frank",
                                                        "age": 2147483648})


class TestEntityRead(DefaultMixin):
    def test_get_entity(self, dbsession):
        jack = self.get_default_entity(dbsession)
        expected = {
            'id': jack.id,
            'name': jack.name,
            'slug': jack.slug,
            'deleted': jack.deleted,
            'age': 10,
            'friends': [],
            'born': None,
            'nickname': 'jack',
            'fav_color': ['blue', 'red']
        }
        data = get_entity(dbsession, id_or_slug=jack.id, schema=jack.schema)
        assert data == expected

        data = get_entity(dbsession, id_or_slug=jack.slug, schema=jack.schema)
        assert data == expected

    def test_raise_on_entity_doesnt_exist(self, dbsession):
        with pytest.raises(MissingEntityException):
            get_entity(dbsession, id_or_slug=9999999999, schema=Schema())

    def test_raise_on_entity_doesnt_belong_to_schema(self, dbsession):
        p = self.get_default_entity(dbsession)
        s = Schema(name='test', slug='test')
        dbsession.add(s)
        dbsession.flush()
        with pytest.raises(MissingEntityException):
            get_entity(dbsession, id_or_slug=p.id, schema=s)

    def test_get_entities(self, dbsession):
        # test default behavior: return not deleted entities
        schema = self.get_default_schema(dbsession)
        e = Entity(slug='Test', name='test', schema_id=schema.id, deleted=True)
        dbsession.add(e)
        dbsession.flush()

        ents = get_entities(dbsession, schema=schema).items
        
        assert len(ents) == 2

        default_field_list = {'id', 'slug', 'deleted', 'age', 'name'}
        ent = ents[1]
        jane = self.get_default_entities(dbsession)["Jane"]
        assert set(ent.keys()) == default_field_list
        assert ent['id'] == jane.id
        assert ent['slug'] == 'Jane'
        assert ent['deleted'] is False
        assert ent['age'] == 12

    def test_get_deleted_only(self, dbsession):
        entity = self.get_default_entity(dbsession)
        entity.deleted = True
        dbsession.flush()

        ents = get_entities(dbsession, schema=entity.schema, deleted_only=True).items
        assert len(ents) == 1
        assert ents[0]['id'] == entity.id
    
    def test_get_all(self, dbsession):
        entity = self.get_default_entities(dbsession)["Jane"]
        entity.deleted = True
        dbsession.flush()

        ents = get_entities(dbsession, schema=entity.schema, all=True).items
        assert len(ents) == 2
        assert not ents[0]['deleted'] and ents[1]['deleted']

    def test_get_all_fields(self, dbsession):
        schema = self.get_default_schema(dbsession)
        ents = get_entities(dbsession, schema=schema, all_fields=True).items
        assert len(ents) == 2
        
        ent = ents[1]
        assert ent['slug'] == 'Jane'
        assert ent['name'] == 'Jane'
        assert ent['deleted'] is False
        assert ent['age'] == 12
        assert ent['born'] is None
        assert ent['friends'] == [self.get_default_entity(dbsession).id]
        assert ent['nickname'] == 'jane'

    def test_offset_and_limit(self, dbsession):
        schema = self.get_default_schema(dbsession)
        
        res = get_entities(dbsession, schema=schema, params=Params(size=1, page=1))
        total, ents = res.total, res.items
        assert len(ents) == 1
        assert ents[0]['slug'] == 'Jack'
        assert total == 2

        res = get_entities(dbsession, schema=schema, params=Params(size=1, page=2))
        total, ents = res.total, res.items
        assert len(ents) == 1
        assert ents[0]['slug'] == 'Jane'
        assert total == 2

        res = get_entities(dbsession, schema=schema, params=Params(size=10, page=2))
        total, ents = res.total, res.items
        assert len(ents) == 0
        assert total == 2

    @pytest.mark.parametrize(['filters', 'ent_len', 'slugs'], [
        ({'age': 10},                 1, ['Jack']),
        ({'age.eq': 10},              1, ['Jack']),
        ({'age.ge': 10},              2, ['Jack', 'Jane']),
        ({'age.gt': 10},              1, ['Jane']),
        ({'age.le': 10},              1, ['Jack']),
        ({'age.lt': 10},              0, []),
        ({'age.ne': 10},              1, ['Jane']),
        ({'slug.starts': 'Ja'},       2, ['Jack', 'Jane']),
        ({'slug.contains': 'ck'},     1, ['Jack']),
        ({'name': 'Jane'},            1, ['Jane']),
        ({'nickname': 'jane'},        1, ['Jane']),
        ({'nickname.ne': 'jack'},     1, ['Jane']),
        ({'nickname.regexp': '^ja'},  2, ['Jack', 'Jane']),
        ({'nickname.contains': 'ne'}, 1, ['Jane']),
        ({'fav_color.contains': 'b'}, 2, ['Jack', 'Jane']),
        ({'fav_color.eq': 'black'},   1, ['Jane']),
        ({'fav_color.ne': 'black'},   2, ['Jack', 'Jane'])  # still returns both even though Jane has black fav_color, but also has red
    ])
    def test_get_with_filter(self, dbsession, filters, ent_len, slugs):
        schema = self.get_default_schema(dbsession)
        res = get_entities(dbsession, schema=schema, filters=filters)
        total, ents = res.total, res.items
        assert len(ents) == ent_len == total
        assert [i['slug'] for i in ents] == slugs

    def test_get_with_multiple_filters_for_same_attr(self, dbsession):
        schema = self.get_default_schema(dbsession)

        filters = {'age.gt': 9, 'age.ne': 10}
        ents = get_entities(dbsession, schema=schema, filters=filters).items
        assert len(ents) == 1 and ents[0]['slug'] == 'Jane'

        filters = {'age.gt': 9, 'age.ne': 10, 'age.lt': 12}
        ents = get_entities(dbsession, schema=schema, filters=filters).items
        assert len(ents) == 0

    @pytest.mark.parametrize(['filters', 'ent_len', 'slugs'], [
        ({'age.gt': 9, 'name.ne': 'Jack'},                   1, ['Jane']),
        ({'name': 'Jack', 'name.ne': 'Jack'},                0, []),
        ({'nickname.ne': 'jane', 'name.ne': 'Jack'},         0, []),
        ({'age.gt': 9, 'age.ne': 10, 'nickname.ne': 'jane'}, 0, []),
    ])
    def test_get_with_multiple_filters(self, dbsession, filters, ent_len, slugs):
        schema = self.get_default_schema(dbsession)

        ents = get_entities(dbsession, schema=schema, filters=filters).items
        assert len(ents) == ent_len
        assert [i['slug'] for i in ents] == slugs
    
    def test_get_with_filters_and_offset_limit(self, dbsession):
        schema = self.get_default_schema(dbsession)
        
        filters = {'age.gt': 0, 'age.lt': 20}
        ents = get_entities(dbsession, schema=schema, filters=filters, params=Params(size=1, page=1)).items
        assert len(ents) == 1 and ents[0]['slug'] == 'Jack'

        ents = get_entities(dbsession, schema=schema, filters=filters, params=Params(size=1, page=2)).items
        assert len(ents) == 1 and ents[0]['slug'] == 'Jane'

        ents = get_entities(dbsession, schema=schema, filters=filters, params=Params(size=10, page=2)).items
        assert len(ents) == 0

    @pytest.mark.parametrize(['params', 'ent_len', 'slugs'], [
        ({},                                  1, ['Jane']),
        ({'all': True},                       2, ['Jack', 'Jane']),
        ({'params': Params(size=1, page=2)},  0, []),
        ({'deleted_only': True},              1, ['Jack']),
        ({'deleted_only': True, 'params': Params(size=1, page=2)}, 0, [])
    ])
    def test_get_with_filters_and_deleted(self, dbsession, params, ent_len, slugs):
        entity = self.get_default_entity(dbsession)
        entity.deleted = True
        dbsession.flush()
        filters = {'age.gt': 0, 'age.lt': 20}
        ents = get_entities(dbsession, schema=entity.schema, filters=filters, **params).items
        assert len(ents) == ent_len
        assert [i['slug'] for i in ents] == slugs

    def test_raise_on_invalid_filters(self, dbsession):
        schema = self.get_default_schema(dbsession)

        filters = {'age.gt': 0, 'age.lt': 20, 'qwer.qwrt': 2323}
        with pytest.raises(InvalidFilterAttributeException):
            get_entities(dbsession, schema=schema, filters=filters).items

        filters = {'age.gt': 0, 'age.lt': 20, 'age.qwertyu': 3104}
        with pytest.raises(InvalidFilterOperatorException):
            get_entities(dbsession, schema=schema, filters=filters).items

        filters = {'age.gt': 0, 'friends.lt': 20}  # we can't filter friends because it's a listed type
        with pytest.raises(InvalidFilterAttributeException):
            get_entities(dbsession, schema=schema, filters=filters).items


class TestEntityUpdate(DefaultMixin):
    def _default_friends(self, db: Session) -> typing.List[int]:
        return [e.id for e in self.get_default_entities(db).values()]

    def asserts_after_entities_update(self, db: Session, born_time: datetime):
        ents = self.get_default_entities(db)
        e = ents["test"]
        assert e.name == 'Jack'
        assert e.get('age', db).value == 10
        assert e.get('born', db).value.astimezone(timezone.utc) == born_time.astimezone(
            timezone.utc)
        assert [i.value for i in e.get('friends', db)] == self._default_friends(db)
        assert e.get('nickname', db) is None
        nicknames = db.execute(
            select(ValueStr)
                .where(Attribute.name == 'nickname')
                .join(Attribute)
        ).scalars().all()
        assert len(nicknames) == 1, "nickname for entity 1 wasn't deleted from database"

        e = ents["test2"]
        assert e.name == 'Jane'
        assert e.get('nickname', db).value == 'test'
        nicknames = db.execute(
            select(ValueStr)
                .where(Attribute.name == 'nickname')
                .join(Attribute)
        ).scalars().all()
        assert len(nicknames) == 1, "nickname for entity 2 wasn't deleted from database"

    def test_update(self, dbsession):
        time = datetime.now(timezone(timedelta(hours=-4)))
        data = {
            'slug': 'test',
            'nickname': None,
            'born': time,
            'friends': self._default_friends(dbsession),
        }
        entity = self.get_default_entity(dbsession)
        update_entity(dbsession, id_or_slug=entity.id, schema_id=entity.schema_id, data=data)

        data = {
            'slug': 'test2',
            'nickname': 'test'
        }
        update_entity(dbsession, id_or_slug='Jane', schema_id=entity.schema_id, data=data)
        self.asserts_after_entities_update(dbsession, born_time=time)

    def test_no_changes(self, dbsession):
        schema = self.get_default_schema(dbsession)
        orig_entity = get_entity(db=dbsession, id_or_slug=self._default_entity_slug, schema=schema)
        update_entity(
            db=dbsession,
            id_or_slug=orig_entity["id"],
            schema_id=schema.id,
            data={
                "age": orig_entity["age"],
                "born": orig_entity["born"],
                "slug": orig_entity["slug"]
            }
        )
        updated_entity = get_entity(db=dbsession, id_or_slug=self._default_entity_slug,
                                    schema=schema)
        for attr in ("age", "born", "nickname"):
            assert orig_entity.get(attr, None) == updated_entity.get(attr, None)

    def test_no_raise_with_empty_optional_single_fk_field(self, dbsession):
        entity = self.get_default_entity(dbsession)
        attr = dbsession.execute(select(Attribute).where(Attribute.name == 'address')).scalar()
        attr_def = AttributeDefinition(
            schema_id=entity.schema_id,
            attribute=attr,
            required=False,
            key=False,
            unique=False,
            list=False
        )
        dbsession.add(attr_def)
        dbsession.commit()
        data = {
            'name': 'Mike',
            'slug': 'Mike',
            'address': None,
        }
        update_entity(dbsession, id_or_slug=entity.id, schema_id=entity.schema_id, data=data)

    def test_raise_on_entity_doesnt_exist(self, dbsession):
        schema = self.get_default_schema(dbsession)
        with pytest.raises(MissingEntityException):
            update_entity(dbsession, id_or_slug=9999, schema_id=schema.id, data={})

        with pytest.raises(MissingEntityException):
            update_entity(dbsession, id_or_slug='qwertyuiop', schema_id=schema.id, data={})

        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([s, e])
        dbsession.flush()
        with pytest.raises(MissingEntityException):
            update_entity(dbsession, id_or_slug='test', schema_id=schema.id, data={})

    def test_raise_on_schema_is_deleted(self, dbsession):
        entity = self.get_default_entity(dbsession)
        entity.schema.deleted = True
        dbsession.flush()

        with pytest.raises(MissingSchemaException):
            update_entity(dbsession, id_or_slug=entity.id, schema_id=entity.schema_id, data={})

    def test_raise_on_entity_already_exists(self, dbsession):
        jack = self.get_default_entity(dbsession)
        data = {'slug': 'Jane'}
        with pytest.raises(EntityExistsException):
            update_entity(dbsession, id_or_slug=jack.id, schema_id=jack.schema_id, data=data)

    def test_no_raise_on_changing_to_same_slug(self, dbsession):
        jack = self.get_default_entity(dbsession)
        data = {'slug': 'Jack'}
        update_entity(dbsession, id_or_slug=jack.id, schema_id=jack.schema_id, data=data)

    def test_raise_on_attribute_not_defined_on_schema(self, dbsession):
        jack = self.get_default_entity(dbsession)
        data = {'not_existing_attr': 50000}
        with pytest.raises(AttributeNotDefinedException):
            update_entity(dbsession, id_or_slug=jack.id, schema_id=jack.schema_id, data=data)
        dbsession.rollback()
        
        data = {'address': 1234}
        with pytest.raises(AttributeNotDefinedException):
            update_entity(dbsession, id_or_slug=jack.id, schema_id=jack.schema_id, data=data)

    def test_raise_on_deleting_required_value(self, dbsession):
        jack = self.get_default_entity(dbsession)
        data = {'age': None}
        with pytest.raises(RequiredFieldException):
            update_entity(dbsession, id_or_slug=jack.id, schema_id=jack.schema_id, data=data)

    def test_raise_on_passing_list_for_not_listed_attr(self, dbsession):
        jack = self.get_default_entity(dbsession)
        data = {'age': [1, 2, 3, 4, 5]}
        with pytest.raises(NotListedAttributeException):
            update_entity(dbsession, id_or_slug=jack.id, schema_id=jack.schema_id, data=data)

    def test_raise_on_fk_entity_doesnt_exist(self, dbsession):
        jack = self.get_default_entity(dbsession)
        data = {'friends': [9999999999]}
        with pytest.raises(MissingEntityException):
            update_entity(dbsession, id_or_slug=jack.id, schema_id=jack.schema_id, data=data)

    def test_raise_on_fk_entity_is_from_wrong_schema(self, dbsession):
        jack = self.get_default_entity(dbsession)
        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([s, e])
        dbsession.flush()

        data = {'friends': [e.id]}
        with pytest.raises(WrongSchemaToBindException):
            update_entity(dbsession, id_or_slug=jack.id, schema_id=jack.schema_id, data=data)

    def test_raise_on_non_unique_value(self, dbsession):
        jack = self.get_default_entity(dbsession)
        data = {'nickname': 'jane'}
        with pytest.raises(UniqueValueException):
            update_entity(dbsession, id_or_slug=jack.id, schema_id=jack.schema_id, data=data)

    def test_no_raise_on_non_unique_if_existing_is_deleted(self, dbsession):
        jane = self.get_default_entities(dbsession)["Jane"]
        jane.deleted = True
        dbsession.flush()
        data = {'nickname': 'jane'}
        update_entity(dbsession, id_or_slug='Jack', schema_id=jane.schema_id, data=data)
        e = dbsession.execute(select(Entity).where(Entity.slug == 'Jack')).scalar()
        assert e.get('nickname', dbsession).value == 'jane'

    def test_restore(self, dbsession):
        """
        Test that updating a deleted entity restores it implicitly
        """
        e = self.get_default_entity(dbsession)
        delete_entity(dbsession, id_or_slug=e.id, schema_id=e.schema_id)

        dbsession.refresh(e)
        assert e.deleted is True

        data = {'slug': e.slug}
        update_entity(dbsession, id_or_slug=e.id, schema_id=e.schema_id, data=data)

        dbsession.refresh(e)
        assert e.deleted is False


class TestEntityDelete(DefaultMixin):
    def asserts_after_entity_delete(self, db: Session):
        entities = db.execute(select(Entity)).scalars().all()
        assert len(entities) == 2
        e = self.get_default_entity(db)
        assert e.deleted

    def test_delete_by_id(self, dbsession):
        e = self.get_default_entity(dbsession)
        delete_entity(dbsession, id_or_slug=e.id, schema_id=e.schema_id)
        self.asserts_after_entity_delete(db=dbsession)

    def test_delete_by_slug(self, dbsession):
        e = self.get_default_entity(dbsession)
        delete_entity(dbsession, id_or_slug=e.slug, schema_id=e.schema_id)
        self.asserts_after_entity_delete(db=dbsession)

    @pytest.mark.parametrize('id_or_slug', [9999999999, 'qwertyu'])
    def test_raise_on_entity_doesnt_exist(self, dbsession, id_or_slug):
        schema = self.get_default_schema(dbsession)
        with pytest.raises(MissingEntityException):
            delete_entity(dbsession, id_or_slug=id_or_slug, schema_id=schema.id)

    def test_raise_on_already_deleted(self, dbsession):
        entity = self.get_default_entity(dbsession)
        entity.deleted = True
        dbsession.flush()
        with pytest.raises(MissingEntityException):
            delete_entity(dbsession, id_or_slug=entity.id, schema_id=entity.schema_id)


class TestRestoreEntity(DefaultMixin):
    def asserts_after_entity_restore(self, db: Session):
        entities = db.execute(select(Entity)).scalars().all()
        assert len(entities) == 2
        e = self.get_default_entity(db)
        assert e.deleted is False

    def test_restore_by_id(self, dbsession):
        e = self.get_default_entity(dbsession)
        e.deleted = True
        dbsession.flush()
        restore_entity(dbsession, id_or_slug=e.id, schema_id=e.schema_id)
        self.asserts_after_entity_restore(db=dbsession)

    def test_restore_by_slug(self, dbsession):
        e = self.get_default_entity(dbsession)
        e.deleted = True
        dbsession.flush()
        restore_entity(dbsession, id_or_slug=e.slug, schema_id=e.schema_id)
        self.asserts_after_entity_restore(db=dbsession)
