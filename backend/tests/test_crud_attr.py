import pytest

from ..config import *
from ..crud import *
from ..models import *
from ..schemas import *


class TestAttributeCreate:
    def test_create(self, dbsession):
        attr = AttributeCreateSchema(name='test', type=AttrTypeMapping.STR)
        attr = create_attribute(dbsession, data=attr)
        attr = dbsession.execute(select(Attribute).where(Attribute.name == 'test')).scalar()
        assert attr is not None
        assert attr.type == AttrType.STR

    def test_create_with_same_name(self, dbsession):
        str_nickname = dbsession.execute(select(Attribute).where(Attribute.name == 'nickname')).scalar()
        int_nickname = create_attribute(dbsession, data=AttributeCreateSchema(name='nickname', type=AttrTypeMapping.INT))
        assert int_nickname.id != str_nickname.id
        assert int_nickname.type != str_nickname.type
        assert int_nickname.name == str_nickname.name

    def test_return_existing_on_duplicate(self, dbsession):
        nickname = dbsession.execute(select(Attribute).where(Attribute.name == 'nickname')).scalar()
        attr = create_attribute(dbsession, data=AttributeCreateSchema(name='nickname', type=AttrTypeMapping[nickname.type.name]))
        assert attr.id == nickname.id

    def test_no_commit(self, dbsession):
        attrs = dbsession.execute(select(Attribute).where(Attribute.name == 'test')).scalars().all()
        assert not len(attrs)

        sch = AttributeCreateSchema(name='test', type=AttrTypeMapping.STR)
        attr1 = create_attribute(dbsession, data=sch, commit=False)
        dbsession.flush()
        
        attrs = dbsession.execute(select(Attribute).where(Attribute.name == 'test')).scalars().all()
        assert len(attrs) == 1

        dbsession.rollback()
        
        attr2 = create_attribute(dbsession, data=sch)
        attrs = dbsession.execute(select(Attribute).where(Attribute.name == 'test')).scalars().all()
        assert len(attrs) == 1
        assert attr1.id != attr2.id

    def test_raise_on_reserved_attr_name(self, dbsession):
        for name in RESERVED_ATTR_NAMES:
            sch = AttributeCreateSchema(name=name, type=AttrTypeMapping.INT)
            with pytest.raises(ReservedAttributeException):
                create_attribute(dbsession, data=sch)


class TestAttributeRead:
    def test_get_attribute(self, dbsession):
        born = dbsession.execute(
            select(Attribute).where(Attribute.name == 'born')
        ).scalar()
        attr = get_attribute(dbsession, attr_id=born.id)
        assert attr == born

    def test_get_attributes(self, dbsession):
        attrs = get_attributes(dbsession)
        assert len(attrs) == 8
        
        names = {'age', 'born', 'friends', 'address', 'nickname', 'fav_color'}
        assert set([i.name for i in attrs]) == names

    def test_raise_on_attr_doesnt_exist(self, dbsession):
        with pytest.raises(MissingAttributeException):
            get_attribute(dbsession, attr_id=999999999)