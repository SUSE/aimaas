import pytest

from ..schemas import validate_slug


slugs = [
    ('hello', True),
    ('Hello', True),
    ('-', False),
    ('hello-', False),
    ('-hello', False),
    ('-hello-', False),
    ('hello-world', True),
    ('hello---', False),
    ('hello-$-world', False),
    ('hello-456-world4', True),
    ('hello-456-wWorld', True),
    ('456-hello', False),
    ('456-World', False),
    ('456', False)
]


@pytest.mark.parametrize('test_input,is_valid', slugs)
def test_validate_slug(test_input, is_valid):
    if is_valid:
        assert validate_slug(None, test_input) == test_input
    else:
        with pytest.raises(ValueError):
            validate_slug(None, test_input)
 