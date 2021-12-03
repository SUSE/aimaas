import pytest

from ..config import *
from ..crud import *
from ..models import *
from ..exceptions import *


def asserts_after_entities_create(db: Session):
    born = datetime(1990, 6, 30, tzinfo=timezone.utc)
    tz_born = datetime(1983, 10, 31, tzinfo=timezone(timedelta(hours=2)))
    persons = db.execute(select(Entity).where(Entity.schema_id == 1)).scalars().all()
    assert len(persons) == 5
    assert persons[-2].name == 'John'
    assert persons[-2].slug == 'John'
    assert persons[-2].get('nickname', db).value == 'john'
    assert persons[-2].get('age', db).value == 10
    assert persons[-2].get('born', db).value == born
    assert isinstance(persons[-2].get('age', db), ValueInt)
    assert [i.value for i in persons[-2].get('friends', db)] == [persons[-3].id, 1]
    assert persons[-1].get('born', db).value == tz_born

class TestEntityCreate:
    def test_create(self, dbsession):
        born = datetime(1990, 6, 30, tzinfo=timezone.utc)
        tz_born = datetime(1983, 10, 31, tzinfo=timezone(timedelta(hours=2)))
        p1 = {
            'name': 'Mike',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [],
        }
        p1 = create_entity(dbsession, schema_id=1, data=p1)
        p2 = {
            'name': 'John',
            'slug': 'John',
            'nickname': 'john',
            'age': 10,
            'friends': [p1.id, 1],
            'born': born
        }
        p2 = create_entity(dbsession, schema_id=1, data=p2)

        p3 = {
            'name': 'Pumpkin Jack',
            'slug': 'pumpkin-jack',
            'nickname': 'pumpkin',
            'age': 38,
            'friends': [p1.id, p2.id],
            'born': tz_born
        }
        p3 = create_entity(dbsession, schema_id=1, data=p3)

        asserts_after_entities_create(dbsession)
    
    def test_no_raise_with_empty_optional_single_fk_field(self, dbsession):
        attr = dbsession.execute(select(Attribute).where(Attribute.name == 'address')).scalar()
        attr_def = AttributeDefinition(
            schema_id=1, 
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
        create_entity(dbsession, schema_id=1, data=data)

    def test_raise_on_non_unique_slug(self, dbsession):
        p1 = {
            'name': 'Jack',
            'slug': 'Jack', 
            'nickname': 'test',
            'age': 10,
            'friends': []
        }
        with pytest.raises(EntityExistsException):
            create_entity(dbsession, schema_id=1, data=p1)

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
        with pytest.raises(UniqueValueException):
            create_entity(dbsession, schema_id=1, data=p1)

    def test_no_raise_on_non_unique_value_if_it_is_deleted(self, dbsession):
        jacks = dbsession.execute(select(ValueStr).where(ValueStr.value == 'jack')).scalars().all()
        assert len(jacks) == 1

        dbsession.execute(update(Entity).where(Entity.id == 1).values(deleted=True))
        p1 = {
            'name': 'Jack',
            'slug': 'Jackie',  
            'nickname': 'jack', # <-- already exists in db, but for deleted entity
            'age': 10,
            'friends': []
        }
        e = create_entity(dbsession, schema_id=1, data=p1)
        jacks = dbsession.execute(select(ValueStr).where(ValueStr.value == 'jack')).scalars().all()
        assert len(jacks) == 2
        assert [i.entity_id for i in jacks] == [1, e.id]

    def test_raise_on_schema_doesnt_exist(self, dbsession):
        p = {
            'name': 'somename',
            'slug': 'Some Name',
            'nickname': 'somename',
            'age': 10,
            'friends': [1]
        }
        with pytest.raises(MissingSchemaException):
            create_entity(dbsession, schema_id=99999, data=p)

    def test_raise_on_attr_doesnt_exist(self, dbsession):
        p = {
            'name': 'somename',
            'slug': 'SomeName',
            'nickname': 'somename',
            'age': 10,
            'friends': [1],
            'nonexistent': True
        }
        with pytest.raises(AttributeNotDefinedException):
            create_entity(dbsession, schema_id=1, data=p)

    def test_raise_on_value_cast(self, dbsession):
        p = {
            'name': 'somename',
            'slug': 'SomeName',
            'nickname': 'somename',
            'age': 'INVALID VALUE',
            'friends': [1],
        }
        with pytest.raises(ValueError):
            create_entity(dbsession, schema_id=1, data=p)

    def test_raise_on_passed_list_for_single_value_attr(self, dbsession):
        p = {
            'name': 'somename',
            'slug': 'Somename',
            'nickname': 'somename',
            'age': [1, 2, 3],
            'friends': [1],
        }
        with pytest.raises(NotListedAttributeException):
            create_entity(dbsession, schema_id=1, data=p)

    def test_raise_on_fk_entity_doesnt_exist(self, dbsession):
        p1 = {
            'name': 'mike',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [99999999]
        }
        with pytest.raises(MissingEntityException):
            create_entity(dbsession, schema_id=1, data=p1)

    def test_raise_on_fk_entity_is_deleted(self, dbsession):
        dbsession.execute(update(Entity).where(Entity.id == 1).values(deleted=True))
        p1 = {
            'name': 'mike',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [1]
        }
        with pytest.raises(MissingEntityException):
            create_entity(dbsession, schema_id=1, data=p1)

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
        with pytest.raises(WrongSchemaToBindException):
            create_entity(dbsession, schema_id=1, data=p1)

    def test_raise_on_slug_not_provided(self, dbsession):
        p1 = {
            'nickname': 'mike',
            'age': 10,
            'friends': [1]
        }
        with pytest.raises(RequiredFieldException):
            create_entity(dbsession, schema_id=1, data=p1)

    def test_raise_on_required_field_not_provided(self, dbsession):
        p1 = {
            'slug': 'Mike',
            'name': 'mike',
            'friends': [1]
        }
        with pytest.raises(RequiredFieldException):
            create_entity(dbsession, schema_id=1, data=p1)


class TestEntityRead:
    def test_get_entity(self, dbsession):
        jack = dbsession.execute(select(Entity).where(Entity.slug == 'Jack')).scalar()
        expected = {
            'id': jack.id,
            'name': jack.name,
            'slug': jack.slug,
            'deleted': jack.deleted,
            'age': 10,
            'friends': [],
            'born': None,
            'nickname': 'jack',
            'fav_color': ['red', 'blue']
        }
        data = get_entity(dbsession, id_or_slug=jack.id, schema=jack.schema)
        assert data == expected

        data = get_entity(dbsession, id_or_slug=jack.slug, schema=jack.schema)
        assert data == expected

    def test_raise_on_entity_doesnt_exist(self, dbsession):
        with pytest.raises(MissingEntityException):
            get_entity(dbsession, id_or_slug=9999999999, schema=Schema())

    def test_raise_on_entity_doesnt_belong_to_schema(self, dbsession):
        s = Schema(name='test', slug='test')
        dbsession.add(s)
        dbsession.flush()
        with pytest.raises(MissingEntityException):
            get_entity(dbsession, id_or_slug=1, schema=s)

    def test_get_entities(self, dbsession):
        # test default behavior: return not deleted entities
        e = Entity(slug='Test', name='test', schema_id=1, deleted=True)
        dbsession.add(e)
        dbsession.flush()

        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        ents = get_entities(dbsession, schema=schema).entities
        
        assert len(ents) == 2

        default_field_list = {'id', 'slug', 'deleted', 'age', 'name'}
        ent = ents[1]
        assert set(ent.keys()) == default_field_list
        assert ent['id'] == 2
        assert ent['slug'] == 'Jane'
        assert ent['deleted'] == False
        assert ent['age'] == 12

    def test_get_deleted_only(self, dbsession):
        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        dbsession.execute(update(Entity).where(Entity.id == 2).values(deleted=True))
        dbsession.flush()

        ents = get_entities(dbsession, schema=schema, deleted_only=True).entities
        assert len(ents) == 1
        assert ents[0]['id'] == 2
    
    def test_get_all(self, dbsession):
        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        dbsession.execute(update(Entity).where(Entity.id == 2).values(deleted=True))
        dbsession.flush()

        ents = get_entities(dbsession, schema=schema, all=True).entities
        assert len(ents) == 2
        assert not ents[0]['deleted'] and ents[1]['deleted']

    def test_get_all_fields(self, dbsession):
        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        ents = get_entities(dbsession, schema=schema, all_fields=True).entities
        assert len(ents) == 2
        
        ent = ents[1]
        assert ent['id'] == 2
        assert ent['slug'] == 'Jane'
        assert ent['name'] == 'Jane'
        assert ent['deleted'] == False
        assert ent['age'] == 12
        assert ent['born'] == None
        assert ent['friends'] == [1]
        assert ent['nickname'] == 'jane'

    def test_offset_and_limit(self, dbsession):
        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        
        res = get_entities(dbsession, schema=schema, limit=1)
        total, ents = res.total, res.entities
        assert len(ents) == 1
        assert ents[0]['id'] == 1
        assert total == 2

        res = get_entities(dbsession, schema=schema, limit=1, offset=1)
        total, ents = res.total, res.entities
        assert len(ents) == 1
        assert ents[0]['id'] == 2
        assert total == 2

        res = get_entities(dbsession, schema=schema, offset=10)
        total, ents = res.total, res.entities
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
        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        res = get_entities(dbsession, schema=schema, filters=filters)
        total, ents = res.total, res.entities
        assert len(ents) == ent_len == total
        assert [i['slug'] for i in ents] == slugs

    def test_get_with_multiple_filters_for_same_attr(self, dbsession):
        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()

        filters = {'age.gt': 9, 'age.ne': 10}
        ents = get_entities(dbsession, schema=schema, filters=filters).entities
        assert len(ents) == 1 and ents[0]['slug'] == 'Jane'

        filters = {'age.gt': 9, 'age.ne': 10, 'age.lt': 12}
        ents = get_entities(dbsession, schema=schema, filters=filters).entities
        assert len(ents) == 0

    @pytest.mark.parametrize(['filters', 'ent_len', 'slugs'], [
        ({'age.gt': 9, 'name.ne': 'Jack'},                   1, ['Jane']),
        ({'name': 'Jack', 'name.ne': 'Jack'},                0, []),
        ({'nickname.ne': 'jane', 'name.ne': 'Jack'},         0, []),
        ({'age.gt': 9, 'age.ne': 10, 'nickname.ne': 'jane'}, 0, []),
    ])
    def test_get_with_multiple_filters(self, dbsession, filters, ent_len, slugs):
        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()

        ents = get_entities(dbsession, schema=schema, filters=filters).entities
        assert len(ents) == ent_len
        assert [i['slug'] for i in ents] == slugs
   
    
    def test_get_with_filters_and_offset_limit(self, dbsession):
        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        
        filters = {'age.gt': 0, 'age.lt': 20}
        ents = get_entities(dbsession, schema=schema, limit=1, filters=filters).entities
        assert len(ents) == 1 and ents[0]['slug'] == 'Jack'

        ents = get_entities(dbsession, schema=schema, limit=1, offset=1, filters=filters).entities
        assert len(ents) == 1 and ents[0]['slug'] == 'Jane'

        ents = get_entities(dbsession, schema=schema, offset=2, filters=filters).entities
        assert len(ents) == 0

    @pytest.mark.parametrize(['params', 'ent_len', 'slugs'], [
        ({},                                  1, ['Jane']),
        ({'all': True},                       2, ['Jack', 'Jane']),
        ({'offset': 1},                       0, []),
        ({'deleted_only': True},              1, ['Jack']),
        ({'deleted_only': True, 'offset': 1}, 0, [])
    ])
    def test_get_with_filters_and_deleted(self, dbsession, params, ent_len, slugs):
        dbsession.execute(update(Entity).where(Entity.slug == 'Jack').values(deleted=True))
        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        filters = {'age.gt': 0, 'age.lt': 20}
        ents = get_entities(dbsession, schema=schema, filters=filters, **params).entities
        assert len(ents) == ent_len
        assert [i['slug'] for i in ents] == slugs

    def test_raise_on_invalid_filters(self, dbsession):
        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()

        filters = {'age.gt': 0, 'age.lt': 20, 'qwer.qwrt': 2323}
        with pytest.raises(InvalidFilterAttributeException):
            get_entities(dbsession, schema=schema, filters=filters).entities

        filters = {'age.gt': 0, 'age.lt': 20, 'age.qwertyu': 3104}
        with pytest.raises(InvalidFilterOperatorException):
            get_entities(dbsession, schema=schema, filters=filters).entities

        filters = {'age.gt': 0, 'friends.lt': 20}  # we can't filter friends because it's a listed type
        with pytest.raises(InvalidFilterAttributeException):
            get_entities(dbsession, schema=schema, filters=filters).entities


def asserts_after_entities_update(db: Session, born_time: datetime):
    e = db.execute(select(Entity).where(Entity.id == 1)).scalar()
    assert e.slug == 'test'
    assert e.get('age', db).value == 10
    assert e.get('born', db).value.replace(tzinfo=timezone.utc) == born_time
    assert [i.value for i in e.get('friends', db)] == [1, 2]
    assert e.get('nickname', db) == None
    nicknames = db.execute(
        select(ValueStr)
        .where(Attribute.name == 'nickname')
        .join(Attribute)
    ).scalars().all()
    assert len(nicknames) == 1, "nickname for entity 1 wasn't deleted from database"

    e = db.execute(select(Entity).where(Entity.id == 2)).scalar()
    assert e.slug == 'test2'
    assert e.get('nickname', db).value == 'test'
    nicknames = db.execute(
        select(ValueStr)
        .where(Attribute.name == 'nickname')
        .join(Attribute)
    ).scalars().all()
    assert len(nicknames) == 1, "nickname for entity 2 wasn't deleted from database"


class TestEntityUpdate:
    def test_update(self, dbsession):
        time = datetime.now(timezone(timedelta(hours=-4)))
        data = {
            'slug': 'test',
            'nickname': None,
            'born': time,
            'friends': [1, 2],
        }
        update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

        data = {
            'slug': 'test2',
            'nickname': 'test'
        }
        update_entity(dbsession, id_or_slug='Jane', schema_id=1, data=data)
        asserts_after_entities_update(dbsession, born_time=time)

    def test_no_raise_with_empty_optional_single_fk_field(self, dbsession):
        attr = dbsession.execute(select(Attribute).where(Attribute.name == 'address')).scalar()
        attr_def = AttributeDefinition(
            schema_id=1, 
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
        update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_raise_on_entity_doesnt_exist(self, dbsession):
        with pytest.raises(MissingEntityException):
            update_entity(dbsession, id_or_slug=9999, schema_id=1, data={})

        with pytest.raises(MissingEntityException):
            update_entity(dbsession, id_or_slug='qwertyuiop', schema_id=1, data={})

        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([s, e])
        dbsession.flush()
        with pytest.raises(MissingEntityException):
            update_entity(dbsession, id_or_slug='test', schema_id=1, data={})

    def test_raise_on_schema_is_deleted(self, dbsession):
        dbsession.execute(update(Schema).where(Schema.id == 1).values(deleted=True))
        with pytest.raises(MissingSchemaException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data={})

    def test_raise_on_entity_already_exists(self, dbsession):
        data = {'slug': 'Jane'}
        with pytest.raises(EntityExistsException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_no_raise_on_changing_to_same_slug(self, dbsession):
        data = {'slug': 'Jack'}
        update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_raise_on_attribute_not_defined_on_schema(self, dbsession):
        data = {'not_existing_attr': 50000}
        with pytest.raises(AttributeNotDefinedException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)
        dbsession.rollback()
        
        data = {'address': 1234}
        with pytest.raises(AttributeNotDefinedException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_raise_on_deleting_required_value(self, dbsession):
        data = {'age': None}
        with pytest.raises(RequiredFieldException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_raise_on_passing_list_for_not_listed_attr(self, dbsession):
        data = {'age': [1, 2, 3, 4, 5]}
        with pytest.raises(NotListedAttributeException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_raise_on_fk_entity_doesnt_exist(self, dbsession):
        data = {'friends': [9999999999]}
        with pytest.raises(MissingEntityException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_raise_on_fk_entity_is_from_wrong_schema(self, dbsession):
        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([s, e])
        dbsession.flush()

        data = {'friends': [e.id]}
        with pytest.raises(WrongSchemaToBindException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_raise_on_non_unique_value(self, dbsession):
        data = {'nickname': 'jane'}
        with pytest.raises(UniqueValueException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_no_raise_on_non_unique_if_existing_is_deleted(self, dbsession):
        dbsession.execute(update(Entity).where(Entity.slug == 'Jane').values(deleted=True))
        data = {'nickname': 'jane'}
        update_entity(dbsession, id_or_slug='Jack', schema_id=1, data=data)
        e = dbsession.execute(select(Entity).where(Entity.slug == 'Jack')).scalar()
        assert e.get('nickname', dbsession).value == 'jane'


def asserts_after_entity_delete(db: Session):
    entities = db.execute(select(Entity)).scalars().all()
    assert len(entities) == 2
    e = db.execute(select(Entity).where(Entity.id == 1)).scalar()
    assert e.deleted

class TestEntityDelete:
    @pytest.mark.parametrize('id_or_slug', [1, 'Jack'])
    def test_delete(self, dbsession, id_or_slug):
        delete_entity(dbsession, id_or_slug=id_or_slug, schema_id=1)
        asserts_after_entity_delete(db=dbsession)

    @pytest.mark.parametrize('id_or_slug', [1234567, 'qwertyu'])
    def test_raise_on_entity_doesnt_exist(self, dbsession, id_or_slug):
        with pytest.raises(MissingEntityException):
            delete_entity(dbsession, id_or_slug=id_or_slug, schema_id=1)

    @pytest.mark.parametrize('id_or_slug', [1, 'Jack'])
    def test_raise_on_already_deleted(self, dbsession, id_or_slug):
        dbsession.execute(update(Entity).where(Entity.id == 1).values(deleted=True))
        with pytest.raises(MissingEntityException):
            delete_entity(dbsession, id_or_slug=id_or_slug, schema_id=1)
        