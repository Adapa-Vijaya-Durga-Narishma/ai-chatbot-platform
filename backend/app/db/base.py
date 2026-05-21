"""
Declarative base shared by all ORM models.
Import Base from here in every model file — never from session.py.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models. No methods or logic here."""
