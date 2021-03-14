from django import template
from django.core import signing
from ..utils import SQL_SALT

register = template.Library()


@register.filter
def sign_sql(value):
    return signing.dumps(value, salt=SQL_SALT)
