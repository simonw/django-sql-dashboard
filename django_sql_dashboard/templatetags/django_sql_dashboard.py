import csv
import io
import json

import bleach
import markdown
from django import template
from django.utils.html import escape, urlize
from django.utils.safestring import mark_safe

from ..utils import sign_sql as sign_sql_original

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
    return sign_sql_original(value)


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


@register.filter
def sql_dashboard_tsv(result):
    writer = io.StringIO()
    csv_writer = csv.writer(writer, delimiter="\t")
    csv_writer.writerow(result["columns"])
    for row in result["row_lists"]:
        csv_writer.writerow(row)
    return writer.getvalue().strip()


@register.filter
def format_cell(value):
    if isinstance(value, str) and value and value[0] in ("{", "["):
        try:
            return mark_safe(
                '<pre class="json">{}</pre>'.format(
                    escape(json.dumps(json.loads(value), indent=2))
                )
            )
        except json.JSONDecodeError:
            pass
    return mark_safe(urlize(value, nofollow=True, autoescape=True))
