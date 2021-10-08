from ..config import *
from ..crud import *
from ..models import *
from ..schemas import *


class TestAttributeCRUD:
    def test_create(self, dbsession):
        attr = AttributeCreateSchema(name='test', type=AttrTypeMapping.STR)
        attr = create_attribute(dbsession, data=attr)
        attr = dbsession.execute(select(Attribute).where(Attribute.name == 'test')).scalar()
        assert attr is not None
        assert attr.type == AttrType.STR

    def test_create_with_same_name(self, dbsession):
        str_name = dbsession.execute(select(Attribute).where(Attribute.name == 'name')).scalar()
        int_name = create_attribute(dbsession, data=AttributeCreateSchema(name='name', type=AttrType.INT))
        assert int_name.id != str_name.id
        assert int_name.type != str_name.type
        assert int_name.name == str_name.name

    def test_return_existing_on_duplicate(self, dbsession):
        name = dbsession.execute(select(Attribute).where(Attribute.name == 'name')).scalar()
        attr = create_attribute(dbsession, data=AttributeCreateSchema(name='name', type=name.type))
        assert attr.id == name.id

    def test_no_commit(self, dbsession):
        attrs = dbsession.execute(select(Attribute).where(Attribute.name == 'test')).scalars().all()
        assert not len(attrs)

        sch = AttributeCreateSchema(name='test', type=AttrType.STR)
        attr1 = create_attribute(dbsession, data=sch, commit=False)
        dbsession.flush()
        
        attrs = dbsession.execute(select(Attribute).where(Attribute.name == 'test')).scalars().all()
        assert len(attrs) == 1

        dbsession.rollback()
        
        attr2 = create_attribute(dbsession, data=sch)
        attrs = dbsession.execute(select(Attribute).where(Attribute.name == 'test')).scalars().all()
        assert len(attrs) == 1
        assert attr1.id != attr2.id

