import pytest

from ..auth.crud import create_group, update_group
from .. import exceptions
from ..schemas.auth import BaseGroupSchema


class TestCrudAuth:
    def test_group_tree(self, dbsession):
        """
        Test that CRUD function allows no circular group relations
        """
        g1 = create_group(data=BaseGroupSchema(name="g1"), db=dbsession)
        g11 = create_group(data=BaseGroupSchema(name="g11", parent_id=g1.id), db=dbsession)
        g111 = create_group(data=BaseGroupSchema(name="g111", parent_id=g11.id), db=dbsession)

        with pytest.raises(expected_exception=exceptions.CircularGroupReferenceException):
            update_group(group_id=g1.id, data=BaseGroupSchema(name=g1.name, parent_id=g111.id),
                         db=dbsession)

    def test_update_group(self, dbsession):
        g2 = create_group(data=BaseGroupSchema(name="g2"), db=dbsession)
        g21 = create_group(data=BaseGroupSchema(name="g21"), db=dbsession)

        assert g21.parent_id is None

        update_group(group_id=g21.id, data=BaseGroupSchema(name="New G11", parent_id=g2.id),
                     db=dbsession)

        assert g21.parent_id == g2.id
        assert g21.name == "New G11"
