"""
Collection of validator functions
"""
import re


def validate_slug(cls, slug: str):
    if slug is None:
        return slug
    if re.match('^[a-zA-Z][-a-zA-Z0-9_.]*[a-zA-Z0-9]$', slug) is None:
        raise ValueError(f'`{slug}` is invalid value for slug field')
    return slug
