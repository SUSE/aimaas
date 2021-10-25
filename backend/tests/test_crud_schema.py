import pytest

from ..config import *
from ..crud import *
from ..models import *
from ..schemas import *
from ..exceptions import *


class TestSchemaCreate:
    def data_for_test(self, db: Session) -> dict:
        color = Attribute(name='color', type=AttrType.STR)
        max_speed =  Attribute(name='max_speed', type=AttrType.INT)
        release_year = Attribute(name='release_year', type=AttrType.DT)
        owner = Attribute(name='owner', type=AttrType.FK)

        db.add_all([color, max_speed, release_year, owner])
        db.commit()

        color_ = AttrDefSchema(
            attr_id=color.id,
            required=False,
            unique=False,
            list=False,
            key=False,
            description='Color of this car'
        )
        max_speed_ = AttrDefSchema(
            attr_id=max_speed.id,
            required=True,
            unique=False,
            list=False,
            key=False
        )
        release_year_ = AttrDefSchema(
            attr_id=release_year.id,
            required=False,
            unique=False,
            list=False,
            key=False
        )
        owner_ = AttrDefSchema(
            attr_id=owner.id,
            required=True,
            unique=False,
            list=False,
            key=False,
            bind_to_schema=1
        )
        return {
            'attrs': {
                'color': color,
                'max_speed': max_speed,
                'release_year': release_year,
                'owner': owner
            },
            'attr_defs': {
                'color': color_,
                'max_speed': max_speed_,
                'release_year': release_year_,
                'owner': owner_
            }
        }

    def test_create(self, dbsession):
        data = self.data_for_test(dbsession)
        car = SchemaCreateSchema(name='Car', slug='car', attributes=list(data['attr_defs'].values()))
        create_schema(dbsession, data=car)
        
        car = dbsession.execute(select(Schema).where(Schema.name == 'Car')).scalar()
        assert car is not None

        attr_defs = dbsession.execute(select(AttributeDefinition).where(AttributeDefinition.schema_id == car.id)).scalars().all()
        assert sorted([i.attribute.name for i in attr_defs]) == sorted(data['attr_defs'])

        color = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == car.id)
            .where(AttributeDefinition.attribute_id == data['attrs']['color'].id)
        ).scalar()
        assert not any([color.required, color.unique, color.list, color.key])
        assert color.description == 'Color of this car'

        ry = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == car.id)
            .where(AttributeDefinition.attribute_id == data['attrs']['release_year'].id)
        ).scalar()
        assert not any([ry.required, ry.unique, ry.list, ry.key])
        assert ry.description is None

        owner = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == car.id)
            .where(AttributeDefinition.attribute_id == data['attrs']['owner'].id)
        ).scalar()
        bfk = dbsession.execute(select(BoundFK).where(BoundFK.attr_def_id == owner.id)).scalars().all()
        assert len(bfk) == 1 and bfk[0].schema.name == 'Person'

    def test_create_with_attr_data(self, dbsession):
        data = self.data_for_test(dbsession)
        test = SchemaCreateSchema(
            name='Test',
            slug='test',
            attributes=[
                AttrDefWithAttrDataSchema(
                    name='test1',
                    type=AttrTypeMapping.STR,
                    required=True,
                    unique=True,
                    list=False,
                    key=True,
                    description='Test 1'
                ),
                AttrDefWithAttrDataSchema(
                    name='test2',
                    type=AttrTypeMapping.STR,
                    required=True,
                    unique=True,
                    list=False,
                    key=True,
                    description='Test 2'
                ),
                data['attr_defs']['color']
            ]
        )
        create_schema(dbsession, data=test)
        
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

    def test_raise_on_reserved_slug(self, dbsession):
        for i in RESERVED_SCHEMA_SLUGS:
            sch = SchemaCreateSchema(name='Person', slug=i, attributes=[])
            with pytest.raises(ReservedSchemaSlugException):
                create_schema(dbsession, data=sch)

    def test_raise_on_duplicate_name_or_slug(self, dbsession):
        sch = SchemaCreateSchema(name='Person', slug='test', attributes=[])
        with pytest.raises(SchemaExistsException):
            create_schema(dbsession, data=sch)
        dbsession.rollback()

        sch = SchemaCreateSchema(name='Test', slug='person', attributes=[])
        with pytest.raises(SchemaExistsException):
            create_schema(dbsession, data=sch)
        dbsession.rollback()

    def test_raise_on_nonexistent_attr_id(self, dbsession):
        nonexistent = AttrDefSchema(
            attr_id=99999,
            required=True,
            unique=True,
            list=False,
            key=True,
            description='Nonexistent attribute'
        )
        sch = SchemaCreateSchema(name='Test', slug='test', attributes=[nonexistent])
        with pytest.raises(MissingAttributeException):
            create_schema(dbsession, data=sch)

    def test_raise_on_empty_schema_when_binding(self, dbsession):
        data = self.data_for_test(dbsession)
        no_schema = AttrDefSchema(
            attr_id=data['attrs']['owner'].id,
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
        data = self.data_for_test(dbsession)
        nonexistent = AttrDefSchema(
            attr_id=data['attrs']['owner'].id,
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
        data = self.data_for_test(dbsession)
        attr_def = AttrDefSchema(
            attr_id=data['attrs']['owner'].id,
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
        data = self.data_for_test(dbsession)

        test = SchemaCreateSchema(
            name='Test',
            slug='test',
            attributes=[
                AttrDefWithAttrDataSchema(
                    name='test1',
                    type=AttrTypeMapping.STR,
                    required=True,
                    unique=True,
                    list=False,
                    key=True,
                    description='Test 1'
                ),
                AttrDefWithAttrDataSchema(
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
                AttrDefWithAttrDataSchema(
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


class TestSchemaUpdate:
    def test_update(self, dbsession):
        attr = dbsession.execute(select(Attribute).where(Attribute.name == 'address')).scalar()
        attr_def = dbsession.execute(
            select(AttributeDefinition)
            .join(Attribute)
            .where(Attribute.name == 'age')
            .where(AttributeDefinition.schema_id == 1)
        ).scalar()
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[
                AttributeDefinitionUpdateSchema(
                    attr_def_id=attr_def.id,
                    required=False,
                    unique=False,
                    list=False,
                    key=False,
                    description='Age of this person'
                )
            ], 
            add_attributes=[
                AttrDefSchema(
                    attr_id=attr.id,
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bind_to_schema=-1
                )
            ]
        )
        update_schema(dbsession, id_or_slug='person', data=upd_schema)

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
            .where(AttributeDefinition.attribute_id == attr.id)
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

    def test_update_attr_def_with_name(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[
                AttributeDefinitionUpdateWithNameSchema(
                    name='age',
                    required=False,
                    unique=False,
                    list=False,
                    key=False,
                    description='Age of this person'
                )
            ], 
            add_attributes=[]
        )
        update_schema(dbsession, id_or_slug=1, data=upd_schema)

        age_def = dbsession.execute(
            select(AttributeDefinition)
            .join(Attribute)
            .where(Attribute.name == 'age')
            .where(AttributeDefinition.schema_id == 1)
        ).scalar()
        assert age_def is not None
        assert not any([age_def.required, age_def.unique, age_def.list, age_def.key])

    def test_update_with_attr_data(self, dbsession, engine):
        attr = dbsession.execute(select(Attribute).where(Attribute.name == 'address')).scalar()
        attr_def = dbsession.execute(
            select(AttributeDefinition)
            .join(Attribute)
            .where(Attribute.name == 'age')
            .where(AttributeDefinition.schema_id == 1)
        ).scalar()
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[
                AttributeDefinitionUpdateSchema(
                    attr_def_id=attr_def.id,
                    required=False,
                    unique=False,
                    list=False,
                    key=False,
                    description='Age of this person'
                )
            ], 
            add_attributes=[
                AttrDefSchema(
                    attr_id=attr.id,
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bind_to_schema=-1
                ),
                AttrDefWithAttrDataSchema(
                    name='test',
                    type=AttrTypeMapping.FK,
                    required=False,
                    unique=False,
                    list=False,
                    key=False,
                    description='Test',
                    bind_to_schema=-1
                )
            ]
        )
        update_schema(dbsession, id_or_slug=1, data=upd_schema)

        address_def = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.attribute_id == attr.id)
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

    def test_raise_on_reserved_slig(self, dbsession):
        for i in RESERVED_SCHEMA_SLUGS:
            upd_schema = SchemaUpdateSchema(
                name='Test', 
                slug=i, 
                update_attributes=[], 
                add_attributes=[]
            )
            with pytest.raises(ReservedSchemaSlugException):
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

    def test_raise_on_attr_def_doesnt_exist(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[
                AttributeDefinitionUpdateSchema(
                    attr_def_id=9999999,
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                )
            ], 
            add_attributes=[]
        )
        with pytest.raises(AttributeNotDefinedException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)

    def test_raise_on_convert_list_to_single(self, dbsession):
        attr = dbsession.execute(select(Attribute).where(Attribute.name == 'friends')).scalar()
        attr_def = dbsession.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == 1)
            .where(AttributeDefinition.attribute_id == attr.id)
        ).scalar()
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[
                AttributeDefinitionUpdateSchema(
                    attr_def_id=attr_def.id,
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

    def test_raise_on_attr_doesnt_exist(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[], 
            add_attributes=[
                AttrDefSchema(
                    attr_id=99999999999,
                    required=True,
                    unique=True,
                    list=True,
                    key=True
                )
            ]
        )
        with pytest.raises(MissingAttributeException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)

    def test_raise_on_attr_def_already_exists(self, dbsession):
        attr = dbsession.execute(select(Attribute).where(Attribute.name == 'born')).scalar()
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[], 
            add_attributes=[
                AttrDefSchema(
                    attr_id=attr.id,
                    required=True,
                    unique=True,
                    list=True,
                    key=True
                )
            ]
        )
        with pytest.raises(AttributeAlreadyDefinedException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)
        dbsession.rollback()

        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[], 
            add_attributes=[
                AttrDefWithAttrDataSchema(
                    name='nickname',
                    type=AttrTypeMapping.DT,
                    required=True,
                    unique=True,
                    list=True,
                    key=True
                )
            ]
        )
        with pytest.raises(AttributeAlreadyDefinedException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)
            
    def test_raise_on_nonexistent_schema_when_binding(self, dbsession):
        attr = dbsession.execute(
            select(Attribute)
            .where(Attribute.name == 'address')
        ).scalar()
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[], 
            add_attributes=[
                AttrDefSchema(
                    attr_id=attr.id,
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
        attr = dbsession.execute(
            select(Attribute)
            .where(Attribute.name == 'address')
        ).scalar()
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            update_attributes=[], 
            add_attributes=[
                AttrDefSchema(
                    attr_id=attr.id,
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
                    attr_id=address.id,
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bind_to_schema=-1
                ),
                AttrDefSchema(
                    attr_id=address.id,
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
                    attr_id=address.id,
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bind_to_schema=-1
                ),
                AttrDefWithAttrDataSchema(
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
   

class TestSchemaDelete:
    @pytest.mark.parametrize('id_or_slug', [1, 'person'])
    def test_delete(self, dbsession, id_or_slug):
        delete_schema(dbsession, id_or_slug=id_or_slug)

        schemas = dbsession.execute(select(Schema)).scalars().all()
        assert len(schemas) == 1
        assert schemas[0].deleted

        entities = dbsession.execute(select(Entity).where(Entity.schema_id == 1)).scalars().all()
        assert len(entities) == 2
        assert all([i.deleted for i in entities])
    
    def test_raise_on_already_deleted(self, dbsession):
        dbsession.execute(update(Schema).where(Schema.id == 1).values(deleted=True))
        with pytest.raises(MissingSchemaException):
            delete_schema(dbsession, id_or_slug=1)

    def test_raise_on_delete_nonexistent(self, dbsession):
        with pytest.raises(MissingSchemaException):
            delete_schema(dbsession, id_or_slug=999999999)

    

    