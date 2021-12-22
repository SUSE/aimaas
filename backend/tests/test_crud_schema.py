import pytest

from ..config import *
from ..crud import *
from ..models import *
from ..schemas import *
from ..exceptions import *


def asserts_after_schema_create(db: Session):
    data = TestSchemaCreate.data_for_test()
    car = db.execute(select(Schema).where(Schema.name == 'Car')).scalar()
    assert car is not None and not car.reviewable

    attr_defs = db.execute(select(AttributeDefinition).where(AttributeDefinition.schema_id == car.id)).scalars().all()
    assert sorted([i.attribute.name for i in attr_defs]) == sorted(data['attr_defs'])

    color = db.execute(
        select(AttributeDefinition)
        .where(AttributeDefinition.schema_id == car.id)
        .join(Attribute)
        .where(Attribute.name == 'color')
    ).scalar()
    assert not any([color.required, color.unique, color.list, color.key])
    assert color.description == 'Color of this car'

    ry = db.execute(
        select(AttributeDefinition)
        .where(AttributeDefinition.schema_id == car.id)
        .join(Attribute)
        .where(Attribute.name == 'release_year')
    ).scalar()
    assert not any([ry.required, ry.unique, ry.list, ry.key])
    assert ry.description is None

    owner = db.execute(
        select(AttributeDefinition)
        .where(AttributeDefinition.schema_id == car.id)
        .join(Attribute)
        .where(Attribute.name == 'owner')
    ).scalar()
    bfk = db.execute(select(BoundFK).where(BoundFK.attr_def_id == owner.id)).scalars().all()
    assert len(bfk) == 1 and bfk[0].schema.name == 'Person'

class TestSchemaCreate:
    @staticmethod
    def data_for_test() -> dict:
        color_ = AttrDefSchema(
            name='color',
            type='STR',
            required=False,
            unique=False,
            list=False,
            key=False,
            description='Color of this car'
        )
        max_speed_ = AttrDefSchema(
            name='max_speed',
            type='INT',
            required=True,
            unique=False,
            list=False,
            key=False
        )
        release_year_ = AttrDefSchema(
            name='release_year',
            type='DT',
            required=False,
            unique=False,
            list=False,
            key=False
        )
        owner_ = AttrDefSchema(
            name='owner',
            type='FK',
            required=True,
            unique=False,
            list=False,
            key=False,
            bind_to_schema=1
        )
        return {
            'attr_defs': {
                'color': color_,
                'max_speed': max_speed_,
                'release_year': release_year_,
                'owner': owner_
            }
        }

    def test_create(self, dbsession):
        data = TestSchemaCreate.data_for_test()
        car = SchemaCreateSchema(name='Car', slug='car', attributes=list(data['attr_defs'].values()))
        create_schema(dbsession, data=car)
        asserts_after_schema_create(dbsession)

    def test_raise_on_duplicate_name_or_slug(self, dbsession):
        sch = SchemaCreateSchema(name='Person', slug='test', attributes=[])
        with pytest.raises(SchemaExistsException):
            create_schema(dbsession, data=sch)
        dbsession.rollback()

        sch = SchemaCreateSchema(name='Test', slug='person', attributes=[])
        with pytest.raises(SchemaExistsException):
            create_schema(dbsession, data=sch)
        dbsession.rollback()

    def test_raise_on_empty_schema_when_binding(self, dbsession):
        no_schema = AttrDefSchema(
            name='friends',
            type='FK',
            required=True,
            unique=True,
            list=False,
            key=True,
            description='No schema passed for binding',
        )
        sch = SchemaCreateSchema(name='Test', slug='test', attributes=[no_schema])
        with pytest.raises(NoSchemaToBindException):
            create_schema(dbsession, data=sch)

    def test_raise_on_nonexistent_schema_when_binding(self, dbsession):
        nonexistent = AttrDefSchema(
            name='owner',
            type='FK',
            required=True,
            unique=True,
            list=False,
            key=True,
            description='Nonexistent schema to bind to',
            bind_to_schema=9999999999
        )
        sch = SchemaCreateSchema(name='Test', slug='test', attributes=[nonexistent])
        with pytest.raises(MissingSchemaException):
            create_schema(dbsession, data=sch)

    def test_raise_on_passed_deleted_schema_for_binding(self, dbsession):
        dbsession.execute(update(Schema).where(Schema.id == 1).values(deleted=True))
        attr_def = AttrDefSchema(
            name='owner',
            type='FK',
            required=True,
            unique=True,
            list=False,
            key=True,
            bind_to_schema=1
        )
       
        sch = SchemaCreateSchema(name='Test', slug='test', attributes=[attr_def])
        with pytest.raises(MissingSchemaException):
            create_schema(dbsession, data=sch)

    def test_raise_on_multiple_attrs_with_same_name(self, dbsession):
        data = TestSchemaCreate.data_for_test()

        test = SchemaCreateSchema(
            name='Test',
            slug='test',
            attributes=[
                AttrDefSchema(
                    name='test1',
                    type=AttrTypeMapping.STR,
                    required=True,
                    unique=True,
                    list=False,
                    key=True,
                    description='Test 1'
                ),
                AttrDefSchema(
                    name='test1',
                    type=AttrTypeMapping.INT,
                    required=True,
                    unique=True,
                    list=False,
                    key=True,
                    description='Test 1 but other type'
                )
            ]
        )
        with pytest.raises(MultipleAttributeOccurencesException):
            create_schema(dbsession, data=test)
        dbsession.rollback()

        test = SchemaCreateSchema(
            name='Test',
            slug='test',
            attributes=[
                AttrDefSchema(
                    name='color',
                    type=AttrTypeMapping.INT,
                    required=True,
                    unique=True,
                    list=False,
                    key=True,
                    description='Color already exists as STR in db'
                ),
                data['attr_defs']['color']
            ]
        )
        with pytest.raises(MultipleAttributeOccurencesException):
            create_schema(dbsession, data=test)
        dbsession.rollback()

        test = SchemaCreateSchema(
            name='Test',
            slug='test',
            attributes=[
                data['attr_defs']['color'],
                data['attr_defs']['color']
            ]
        )
        with pytest.raises(MultipleAttributeOccurencesException):
            create_schema(dbsession, data=test)


class TestSchemaRead:
    def test_get_schema_by_id_and_slug(self, dbsession):
        schema = dbsession.execute(select(Schema).where(Schema.name == 'Person')).scalar()
        assert schema == get_schema(dbsession, id_or_slug=schema.id)
        assert schema == get_schema(dbsession, id_or_slug=schema.slug)

    def test_raise_on_schema_doesnt_exist(self, dbsession):
        with pytest.raises(MissingSchemaException):
            get_schema(dbsession, id_or_slug=999999999)

        with pytest.raises(MissingSchemaException):
            get_schema(dbsession, id_or_slug='qwertyuiop')
    
    def test_get_schemas(self, dbsession):
        # test default behavior: return not deleted schemas
        test = Schema(name='Test', slug='test', deleted=True)
        dbsession.add(test)
        dbsession.flush()

        schema = dbsession.execute(select(Schema).where(Schema.name == 'Person')).scalar()
        schemas = get_schemas(dbsession)
        assert len(schemas) == 1
        assert schemas[0] == schema

    def test_get_all(self, dbsession):
        test = Schema(name='Test', slug='test', deleted=True)
        dbsession.add(test)
        dbsession.flush()

        schemas = get_schemas(dbsession, all=True)
        assert len(schemas) == 2

    def test_get_deleted_only(self, dbsession):
        test = Schema(name='Test', slug='test', deleted=True)
        dbsession.add(test)
        dbsession.flush()

        schemas = get_schemas(dbsession, deleted_only=True)
        assert len(schemas) == 1
        assert schemas[0] == test


def asserts_after_schema_update(db: Session):
    friends = db.execute(
        select(AttributeDefinition)
        .join(Attribute)
        .where(Attribute.name == 'friends')
        .where(AttributeDefinition.schema_id == 1)
    ).scalar()
    assert friends is None
    
    age_def = db.execute(
        select(AttributeDefinition)
        .join(Attribute)
        .where(Attribute.name == 'age')
        .where(AttributeDefinition.schema_id == 1)
    ).scalar()
    assert age_def is not None
    assert not any([age_def.required, age_def.unique, age_def.list, age_def.key])

    address_def = db.execute(
        select(AttributeDefinition)
        .join(Attribute)
        .where(Attribute.name == 'address')
        .where(AttributeDefinition.schema_id == 1)
    ).scalar()
    assert address_def is not None
    assert all([address_def.list, address_def.key, address_def.required])
    assert not address_def.unique

    bfk = db.execute(
        select(BoundFK)
        .where(BoundFK.schema_id == 1)
        .where(BoundFK.attr_def_id == address_def.id)
    ).scalar()
    assert bfk is not None

    sch = db.execute(select(Schema).where(Schema.id == 1)).scalar()
    assert sch.name == 'Person' and sch.slug == 'test' and sch.reviewable

class TestSchemaUpdate:
    def test_update(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            slug='test',
            reviewable=True,
            update_attributes=[
                AttrDefUpdateSchema(
                    name='age',
                    required=False,
                    unique=False,
                    list=False,
                    key=False,
                    description='Age of this person'
                )
            ], 
            add_attributes=[
                AttrDefSchema(
                    name='address',
                    type='FK',
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bind_to_schema=-1
                )
            ],
            delete_attributes=['friends']
        )
        update_schema(dbsession, id_or_slug='person', data=upd_schema)
        asserts_after_schema_update(db=dbsession)

    def test_update_with_renaming(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[
                AttrDefUpdateSchema(
                    name='nickname',
                    new_name='nick',
                    required=False,
                    unique=False,
                    list=False,
                    key=False,
                    description='updated'
                )
            ], 
        )
        update_schema(dbsession, id_or_slug=1, data=upd_schema)
        nickname = dbsession.execute(select(Attribute).where(Attribute.name == 'nickname')).scalar()
        assert nickname is not None, 'nickname must be still present in DB'
        attr_def = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == 1)
            .join(Attribute)
            .where(Attribute.name == 'nick')
        ).scalar()
        assert attr_def is not None
        assert not any([attr_def.required, attr_def.unique, attr_def.list, attr_def.key])
        assert attr_def.description == 'updated'


    def test_update_with_renaming_and_adding_new_with_old_name(self, dbsession):
        nickname_id = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == 1)
            .join(Attribute)
            .where(Attribute.name == 'nickname')
        ).scalar().id
        
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[
                AttrDefUpdateSchema(
                    name='nickname',
                    new_name='nick',
                    required=False,
                    unique=False,
                    list=False,
                    key=False,
                    description='updated'
                )
            ], 
            add_attributes=[
                AttrDefSchema(
                    name='nickname',
                    type='DT',
                    required=True,
                    unique=True,
                    list=True,
                    key=True
                )
            ]
        )
        update_schema(dbsession, id_or_slug=1, data=upd_schema)
        dbsession.expire_all()
        nick_id = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == 1)
            .join(Attribute)
            .where(Attribute.name == 'nick')
        ).scalar().id
        assert nickname_id == nick_id

        nickname = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == 1)
            .join(Attribute)
            .where(Attribute.name == 'nickname')
        ).scalar()
        assert nickname.attribute.type == AttrType.DT
        assert all([nickname.required, nickname.list, nickname.key])

    def test_raise_on_renaming_to_already_present_attr(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[
                AttrDefUpdateSchema(
                    name='nickname',
                    new_name='friends',
                    required=False,
                    unique=False,
                    list=False,
                    key=False,
                    description='updated'
                )
            ], 
            add_attributes=[],
            delete_attributes=[]
        )
        with pytest.raises(MultipleAttributeOccurencesException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)
        dbsession.rollback()

    def test_update_with_deleting_attr(self, dbsession):
        initial_count = len(
            dbsession.execute(
                select(AttributeDefinition)
                .where(AttributeDefinition.schema_id == 1)
            ).scalars().all()
        )
        init_entities_count = len(dbsession.execute(select(Entity).where(Entity.schema_id == 1)).scalars().all())
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            delete_attributes=['age', 'born']
        )
        update_schema(dbsession, id_or_slug=1, data=upd_schema)
        attr_defs = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == 1)
        ).scalars().all()
        assert len(attr_defs) == initial_count - 2
        names = [i.attribute.name for i in attr_defs]
        assert 'age' not in names and 'born' not in names
        dbsession.expire_all()
        new_entities_count = len(dbsession.execute(select(Entity).where(Entity.schema_id == 1)).scalars().all())
        assert init_entities_count == new_entities_count

    def test_raise_on_deleting_and_creating_same_attr(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            add_attributes=[
                AttrDefSchema(
                    name='age',
                    type='INT',
                    required=True,
                    unique=True,
                    list=True,
                    key=True
                )
            ],
            delete_attributes=['age']
        )
        with pytest.raises(NoOpChangeException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)

    def test_raise_on_deleting_and_updating_same_attr(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[
                AttrDefUpdateSchema(
                    name='age',
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    description='upd'
                )
            ],
            delete_attributes=['age']
        )
        with pytest.raises(NoOpChangeException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)

    def test_no_raise_on_deleting_and_creating_attr_with_same_name_but_different_type(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            add_attributes=[
                AttrDefSchema(
                    name='age',
                    type='FLOAT',
                    required=True,
                    unique=True,
                    list=True,
                    key=True
                )
            ],
            delete_attributes=['age']
        )
        update_schema(dbsession, id_or_slug=1, data=upd_schema)

    def test_raise_on_schema_doesnt_exist(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[], 
            add_attributes=[]
        )
        with pytest.raises(MissingSchemaException):
            update_schema(dbsession, id_or_slug=99999999, data=upd_schema)

    def test_raise_on_existing_slug_or_name(self, dbsession):
        new_sch = Schema(name='Test', slug='test')
        dbsession.add(new_sch)
        dbsession.flush()
        
        upd_schema = SchemaUpdateSchema(name='Person', slug='test', update_attributes=[], add_attributes=[])
        with pytest.raises(SchemaExistsException):
            update_schema(dbsession, id_or_slug=new_sch.id, data=upd_schema)
        dbsession.rollback()
        dbsession.add(new_sch)
        dbsession.flush()

        upd_schema = SchemaUpdateSchema(name='Test', slug='person', update_attributes=[], add_attributes=[])
        with pytest.raises(SchemaExistsException):
            update_schema(dbsession, id_or_slug=new_sch.id, data=upd_schema)

    def test_raise_on_convert_list_to_single(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[
                AttrDefUpdateSchema(
                    name='friends',
                    required=True,
                    unique=True,
                    list=False,
                    key=True,
                )
            ], 
            add_attributes=[]
        )
        with pytest.raises(ListedToUnlistedException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)

    def test_raise_on_attr_def_already_exists(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[], 
            add_attributes=[
                AttrDefSchema(
                    name='born',
                    type='DT',
                    required=True,
                    unique=True,
                    list=True,
                    key=True
                )
            ]
        )
        # TODO currently works the same way as raise_on_multiple_attrs_with_same_name
        # this one can be removed
        with pytest.raises(MultipleAttributeOccurencesException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)
        dbsession.rollback()
            
    def test_raise_on_nonexistent_schema_when_binding(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[], 
            add_attributes=[
                AttrDefSchema(
                    name='address',
                    type='FK',
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bind_to_schema=999999
                )
            ]
        )
        with pytest.raises(MissingSchemaException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)

    def test_raise_on_schema_not_passed_when_binding(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[], 
            add_attributes=[
                AttrDefSchema(
                    name='address',
                    type='FK',
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                )
            ]
        )
        with pytest.raises(NoSchemaToBindException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)

    def test_raise_on_multiple_attrs_with_same_name(self, dbsession):
        address = dbsession.execute(
            select(Attribute)
            .where(Attribute.name == 'address')
        ).scalar()

        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[], 
            add_attributes=[
                AttrDefSchema(
                    name='address',
                    type='FK',
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bind_to_schema=-1
                ),
                AttrDefSchema(
                    name='address',
                    type='FK',
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bind_to_schema=-1
                )
            ]
        )
        with pytest.raises(MultipleAttributeOccurencesException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)
        dbsession.rollback()


        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[], 
            add_attributes=[
                AttrDefSchema(
                    name='address',
                    type='FK',
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bind_to_schema=-1
                ),
                AttrDefSchema(
                    name='address',
                    type=AttrTypeMapping.DT,
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                )
            ]
        )
        with pytest.raises(MultipleAttributeOccurencesException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)
   

def asserts_after_schema_delete(db: Session):
    schemas = db.execute(select(Schema)).scalars().all()
    assert len(schemas) == 1
    assert schemas[0].deleted

    entities = db.execute(select(Entity).where(Entity.schema_id == 1)).scalars().all()
    assert len(entities) == 2
    assert all([i.deleted for i in entities])

class TestSchemaDelete:
    @pytest.mark.parametrize('id_or_slug', [1, 'person'])
    def test_delete(self, dbsession, id_or_slug):
        delete_schema(dbsession, id_or_slug=id_or_slug)
        asserts_after_schema_delete(db=dbsession)
    
    def test_raise_on_already_deleted(self, dbsession):
        dbsession.execute(update(Schema).where(Schema.id == 1).values(deleted=True))
        with pytest.raises(MissingSchemaException):
            delete_schema(dbsession, id_or_slug=1)

    def test_raise_on_delete_nonexistent(self, dbsession):
        with pytest.raises(MissingSchemaException):
            delete_schema(dbsession, id_or_slug=999999999)

    

    