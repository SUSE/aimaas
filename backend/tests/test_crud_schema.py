from datetime import datetime, timezone
from pydantic.error_wrappers import ValidationError
import pytest
from sqlalchemy import select, update

from ..crud import create_schema, get_schema, get_schemas, update_schema, delete_schema, \
    get_entities, update_entity
from ..exceptions import SchemaExistsException, MissingSchemaException, RequiredFieldException, \
    NoOpChangeException, ListedToUnlistedException, MultipleAttributeOccurencesException
from ..models import Schema, AttributeDefinition, Attribute, AttrType, Entity
from .. schemas import AttrDefSchema, SchemaCreateSchema, AttrTypeMapping, SchemaUpdateSchema


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
            bound_schema_id=1
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
        data = self.data_for_test()
        car = create_schema(dbsession, data=SchemaCreateSchema(
            name='Car', slug='car', attributes=list(data['attr_defs'].values())
        ))

        assert car is not None and not car.reviewable

        attr_defs = dbsession.execute(select(AttributeDefinition).where(
            AttributeDefinition.schema_id == car.id)).scalars().all()
        assert sorted([i.attribute.name for i in attr_defs]) == sorted(data['attr_defs'])

        color = dbsession.execute(
            select(AttributeDefinition)
                .where(AttributeDefinition.schema_id == car.id)
                .join(Attribute)
                .where(Attribute.name == 'color')
        ).scalar()
        assert not any([color.required, color.unique, color.list, color.key])
        assert color.description == 'Color of this car'

        ry = dbsession.execute(
            select(AttributeDefinition)
                .where(AttributeDefinition.schema_id == car.id)
                .join(Attribute)
                .where(Attribute.name == 'release_year')
        ).scalar()
        assert not any([ry.required, ry.unique, ry.list, ry.key])
        assert ry.description is None

        owner = dbsession.execute(
            select(AttributeDefinition)
                .where(AttributeDefinition.schema_id == car.id)
                .join(Attribute)
                .where(Attribute.name == 'owner')
        ).scalar()
        assert owner.bound_schema.name == 'Person'

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
        with pytest.raises(ValidationError):
            no_schema = AttrDefSchema(
                name='friends',
                type='FK',
                required=True,
                unique=True,
                list=False,
                key=True,
                description='No schema passed for binding',
            )

    def test_raise_on_nonexistent_schema_when_binding(self, dbsession):
        nonexistent = AttrDefSchema(
            name='owner',
            type='FK',
            required=True,
            unique=True,
            list=False,
            key=True,
            description='Nonexistent schema to bind to',
            bound_schema_id=9999999999
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
            bound_schema_id=1
        )
       
        sch = SchemaCreateSchema(name='Test', slug='test', attributes=[attr_def])
        with pytest.raises(MissingSchemaException):
            create_schema(dbsession, data=sch)

    def test_raise_on_multiple_attrs_with_same_name(self, dbsession):
        data = self.data_for_test()

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
        assert len(schemas) == 2
        assert schemas[0] == schema

    def test_get_all(self, dbsession):
        test = Schema(name='Test', slug='test', deleted=True)
        dbsession.add(test)
        dbsession.flush()

        schemas = get_schemas(dbsession, all=True)
        assert len(schemas) == 3

    def test_get_deleted_only(self, dbsession):
        test = Schema(name='Test', slug='test', deleted=True)
        dbsession.add(test)
        dbsession.flush()

        schemas = get_schemas(dbsession, deleted_only=True)
        assert len(schemas) == 1
        assert schemas[0] == test


class TestSchemaUpdate:
    default_attributes = [
        AttrDefSchema(
            id=1,
            name='age',
            type="INT",
            required=True,
            unique=False,
            list=False,
            key=True,
            description='Age of this person'
        ),
        AttrDefSchema(
            id=2,
            name='born',
            type='DT',
            required=False,
            unique=False,
            list=False,
            key=False
        ),
        AttrDefSchema(
            id=3,
            name='friends',
            type='FK',
            required=True,
            unique=False,
            list=True,
            key=False,
            bound_schema_id=-1
        ),
        AttrDefSchema(
            id=4,
            name='nickname',
            type='STR',
            required=False,
            unique=True,
            list=False,
            key=False
        ),
        AttrDefSchema(
            id=5,
            name='fav_color',
            type='STR',
            required=False,
            unique=False,
            list=True,
            key=False
        )
    ]

    def test_update(self, dbsession):
        attributes = [a for a in self.default_attributes if a.name != "age"] + [
                AttrDefSchema(
                    id=1,
                    name='age',
                    type='INT',
                    required=False,
                    unique=False,
                    list=False,
                    key=False,
                    description='Age of this person'
                ),
                AttrDefSchema(
                    name='address',
                    type='FK',
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bound_schema_id=-1
                )
            ]
        upd_schema = SchemaUpdateSchema(
            slug='test',
            reviewable=True,
            attributes=attributes
        )
        update_schema(dbsession, id_or_slug='person', data=upd_schema)

        schema = dbsession.query(Schema).filter(Schema.slug == "test").one()
        assert schema.name == 'Person' and schema.slug == 'test'

        attrs = {d.attribute.name: d.attribute.type for d in schema.attr_defs}
        assert attrs.get("friends") == AttrType.FK
        assert attrs.get("address") == AttrType.FK
        assert attrs.get("age") == AttrType.INT

        age = next(iter(d for d in schema.attr_defs if d.attribute.name == "age"))
        assert not any([age.required, age.unique, age.list, age.key])

        address = next(iter(d for d in schema.attr_defs if d.attribute.name == "address"))
        assert all([address.list, address.key, address.required])
        assert not address.unique
        assert address.bound_schema_id == schema.id

    def test_update_with_renaming(self, dbsession):
        attributes = [a for a in self.default_attributes if a.id != 4] + [
                AttrDefSchema(
                    id=4,
                    name='nick',
                    type='STR',
                    required=False,
                    unique=False,
                    list=False,
                    key=False,
                    description='updated'
                )
            ]
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            attributes=attributes,
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
            .join(Attribute)
            .where(Attribute.name == 'nickname')
            .where(AttributeDefinition.schema_id == 1)
        ).scalar().id

        attributes = [a for a in self.default_attributes if a.id != 4] + [
                AttrDefSchema(
                    id=4,
                    name='nick',
                    type='STR',
                    required=False,
                    unique=False,
                    list=False,
                    key=False,
                    description='updated'
                ),
                AttrDefSchema(
                    name='nickname',
                    type='DT',
                    required=True,
                    unique=True,
                    list=True,
                    key=True
                )
            ]

        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            attributes=attributes
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
        attributes = [a for a in self.default_attributes if a.id != 4] + [
                AttrDefSchema(
                    id=4,
                    name='friends',
                    type='INT',
                    required=False,
                    unique=False,
                    list=False,
                    key=False,
                    description='updated'
                )
            ]
        upd_schema = SchemaUpdateSchema(
            name='Test',
            slug='test',
            attributes=attributes
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
            attributes=[a for a in self.default_attributes if a.name not in ['age', 'born']]
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
        attributes = [a for a in self.default_attributes if a.id != 1] + [
                AttrDefSchema(
                    name='age',
                    type='INT',
                    required=True,
                    unique=True,
                    list=True,
                    key=True
                )]
        upd_schema = SchemaUpdateSchema(
            name='Person',
            slug='person',
            attributes=attributes
        )
        with pytest.raises(NoOpChangeException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)

    def test_raise_on_schema_doesnt_exist(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test',
            attributes=[]
        )
        with pytest.raises(MissingSchemaException):
            update_schema(dbsession, id_or_slug=99999999, data=upd_schema)

    def test_raise_on_existing_slug_or_name(self, dbsession):
        new_sch = Schema(name='Test', slug='test')
        dbsession.add(new_sch)
        dbsession.flush()
        
        upd_schema = SchemaUpdateSchema(name='Person', slug='test', attributes=[])
        with pytest.raises(SchemaExistsException):
            update_schema(dbsession, id_or_slug=new_sch.id, data=upd_schema)
        dbsession.rollback()
        dbsession.add(new_sch)
        dbsession.flush()

        upd_schema = SchemaUpdateSchema(name='Test', slug='person', attributes=[])
        with pytest.raises(SchemaExistsException):
            update_schema(dbsession, id_or_slug=new_sch.id, data=upd_schema)

    def test_raise_on_convert_list_to_single(self, dbsession):
        attributes = [a for a in self.default_attributes if a.id != 3] + [
                AttrDefSchema(
                    id=3,
                    name='friends',
                    type="FK",
                    required=True,
                    unique=True,
                    list=False,
                    key=True,
                    bound_schema_id=-1
                )
            ]
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test', 
            attributes=attributes
        )
        with pytest.raises(ListedToUnlistedException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)

    def test_raise_on_attr_def_already_exists(self, dbsession):
        attributes = self.default_attributes + [
                AttrDefSchema(
                    name='born',
                    type='INT',
                    required=True,
                    unique=True,
                    list=True,
                    key=True
                )
            ]
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test',
            attributes=attributes
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
            attributes=self.default_attributes + [
                AttrDefSchema(
                    name='address',
                    type='FK',
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bound_schema_id=999999
                )
            ]
        )
        with pytest.raises(MissingSchemaException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)

    def test_raise_on_schema_not_passed_when_binding(self, dbsession):
        with pytest.raises(ValidationError):
            SchemaUpdateSchema(
                name='Test',
                slug='test',
                attributes=[
                    AttrDefSchema(
                        name='address2',
                        type='FK',
                        required=True,
                        unique=True,
                        list=True,
                        key=True,
                    )
                ]
            )

    def test_raise_on_duplicate_attrs(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test',
            attributes=[
                AttrDefSchema(
                    name='address',
                    type='FK',
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bound_schema_id=-1
                ),
                AttrDefSchema(
                    name='address',
                    type='FK',
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bound_schema_id=-1
                )
            ]
        )
        with pytest.raises(MultipleAttributeOccurencesException):
            update_schema(dbsession, id_or_slug=1, data=upd_schema)

    def test_raise_on_multiple_attrs_with_same_name(self, dbsession):
        upd_schema = SchemaUpdateSchema(
            name='Test', 
            slug='test',
            attributes=[
                AttrDefSchema(
                    name='address',
                    type='FK',
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bound_schema_id=-1
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

    def test_raise_on_invalid_attribute_name(self, dbsession):
        with pytest.raises(ValidationError):
            SchemaUpdateSchema(
                name="Test",
                slug="test",
                attributes=self.default_attributes + [AttrDefSchema(
                    name='403',
                    type="INT",
                    required=True,
                    unique=False,
                    list=False,
                    key=True,
                    description='This is an invalid name'
                )]
            )

    def test_make_attr_required(self, dbsession):
        """
        Make sure that optional attributes (with empty values) can be made required
        """
        attributes = [a for a in self.default_attributes if a.name != "born"] + [
            AttrDefSchema(
                id=2,
                name='born',
                type='DT',
                required=True,
                unique=False,
                list=False,
                key=False
            ),
        ]

        upd_schema = SchemaUpdateSchema(
            attributes=attributes
        )
        update_schema(dbsession, id_or_slug='person', data=upd_schema)

        entities = get_entities(dbsession, get_schema(dbsession, 1)).entities
        assert all(e.get("born", None) is None for e in entities)

        with pytest.raises(RequiredFieldException):
            update_entity(dbsession, 1, 1, {"name": "Frank", "age": 99})


class TestSchemaDelete:
    @pytest.mark.parametrize('id_or_slug', [1, 'person'])
    def test_delete(self, dbsession, id_or_slug):
        schema = delete_schema(dbsession, id_or_slug=id_or_slug)
        assert schema.deleted

        schemas = dbsession.execute(select(Schema)).scalars().all()
        deleted_schema = [s for s in schemas if schema.id == s.id]
        assert len(schemas) == 2
        assert deleted_schema
        assert deleted_schema[0].deleted

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
