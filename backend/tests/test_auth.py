# from ..auth import *
# from ..models import *


# def test_search_perm(dbsession):
#     perm = Permission(id=7)
#     user = User(id=1)
#     res = check_has_perm_in_groups(perm=perm, user=user, db=dbsession)
#     assert res


# def test_check_user_has_perm(dbsession):
#     user = User(id=1)
#     perm1 = Permission(id=1)
#     perm2 = Permission(id=1000)
#     assert check_user_has_perm(user=user, perm=perm1, db=dbsession)
#     assert not check_user_has_perm(user=user, perm=perm2, db=dbsession)