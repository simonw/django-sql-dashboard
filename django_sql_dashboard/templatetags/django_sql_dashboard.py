import bleach
import markdown
from django import template
from django.core import signing
from django.utils.safestring import mark_safe
from ..utils import SQL_SALT


TAGS = [
    "a",
    "abbr",
    "acronym",
    "b",
    "blockquote",
    "code",
    "em",
    "i",
    "li",
    "ol",
    "strong",
    "ul",
    "pre",
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
]
ATTRIBUTES = {"a": ["href"]}

register = template.Library()


@register.filter
def sign_sql(value):
    return signing.dumps(value, salt=SQL_SALT)


@register.filter
def sql_dashboard_bleach(value):
    return mark_safe(
        bleach.clean(
            value,
            tags=TAGS,
            attributes=ATTRIBUTES,
        )
    )


@register.filter
def sql_dashboard_markdown(value):
    return mark_safe(
        bleach.linkify(
            bleach.clean(
                markdown.markdown(
                    value,
                    output_format="html5",
                ),
                tags=TAGS,
                attributes=ATTRIBUTES,
            )
        )
    )
