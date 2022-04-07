import binascii
import json
import re
import urllib.parse
from collections import namedtuple

from django.core import signing
from django.conf import settings
from django.utils.html import escape
from django.utils.safestring import mark_safe

SQL_SALT = "django_sql_dashboard:query"

signer = signing.Signer(salt=SQL_SALT)


def sign_sql(sql):
    return signer.sign(sql)


def unsign_sql(signed_sql, try_object=False):
    # Returns (sql, signature_verified)
    # So we can handle broken signatures
    # Usually this will be a regular string
    try:
        sql = signer.unsign(signed_sql)
        return sql, True
    except signing.BadSignature:
        try:
            value, bad_sig = signed_sql.rsplit(signer.sep, 1)
            return value, False
        except ValueError:
            return signed_sql, False


class Row:
    def __init__(self, values, columns):
        self.values = values
        self.columns = columns
        self.zipped = dict(zip(columns, values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.values[key]
        else:
            return self.zipped[key]

    def __repr__(self):
        return json.dumps(self.zipped)


def displayable_rows(rows):
    fixed = []
    for row in rows:
        fixed_row = []
        for cell in row:
            if isinstance(cell, (dict, list)):
                cell = json.dumps(cell, default=str)
            fixed_row.append(cell)
        fixed.append(fixed_row)
    return fixed


def check_for_base64_upgrade(queries):
    if not queries:
        return
    # Strip of the timing bit if there is one
    queries = [q.split(":")[0] for q in queries]
    # If every query is base64-encoded JSON, return a new querystring
    if not all(is_valid_base64_json(query) for query in queries):
        return
    # Need to decode these and upgrade them to ?sql= links
    sqls = []
    for query in queries:
        sqls.append(sign_sql(json.loads(signing.b64_decode(query.encode()))))
    return "?" + urllib.parse.urlencode({"sql": sqls}, True)


def is_valid_base64_json(s):
    try:
        json.loads(signing.b64_decode(s.encode()))
        return True
    except (json.JSONDecodeError, binascii.Error, UnicodeDecodeError):
        return False


_reserved_words = None


def postgresql_reserved_words(connection):
    global _reserved_words
    if _reserved_words is None:
        with connection.cursor() as cursor:
            cursor.execute("select word from pg_get_keywords() where catcode = 'R'")
            _reserved_words = [row[0] for row in cursor.fetchall()]
    return _reserved_words


_sort_re = re.compile('(^.*) order by "[^"]+"( desc)?$', re.DOTALL)


def apply_sort(sql, sort_column, is_desc=False):
    match = _sort_re.match(sql)
    if match is not None:
        sql = match.group(1)
    else:
        sql = "select * from ({}) as results".format(sql)
    return sql + ' order by "{}"{}'.format(sort_column, " desc" if is_desc else "")


class Parameter:
    extract_re = re.compile(r"\%\(([^\)]+)\)s")

    def __init__(self, name, default_value=""):
        self.name = name
        self.default_value = self.get_sanitized(default_value, for_default=True)

    def ensure_consistency(self, previous):
        if self.name != previous.name:
            raise ValueError("Invalid name for parameter '%s': previously registered with name '%s'" % (self.name, previous.name))
        if self.default_value != "" and self.default_value != previous.default_value:
            raise ValueError("Invalid default value '%s' for parameter '%s': previously registered with default value '%s'" % (self.default_value, self.name, previous.default_value))

    def get_sanitized(self, value, for_default=False):
        if value is None or (for_default and value == "null"):
            return None # represents DB null value
        if not isinstance(value, str):
            raise ValueError("Invalid %svalue for parameter '%s': '%s'" % ("default " if for_default else "", self.name, type(value).__name__))
        return value

    @property
    def value(self):
        return self._value if hasattr(self, "_value") else self.default_value

    @value.setter
    def value(self, new_value):
        self._value = self.get_sanitized(new_value) if new_value != "" else self.default_value
   
    def form_control(self):
        return mark_safe(f"""<label for="qp_{escape(self.name)}">{escape(self.name)}</label>
<input type="text" id="qp_{escape(self.name)}" name="{escape(self.name)}" value="{escape(self.value) if self.value is not None else ""}">""")

    @classmethod
    def extract(cls, sql: str, value_sources: list[dict[str, str]], target: list=[]):
        for found in cls.extract_re.findall(sql):
            # Ensure 'found' is an iterable of capturing groups, even if there is only one capturing group in the regex
            if isinstance(found, str):
                found = [found]
            new_param = cls(*found)

            # Ensure parameters are added only once
            previous_param = next((param for param in target if param.name == new_param.name), None)
            if previous_param:
                new_param.ensure_consistency(previous_param)
            else:
                target.append(new_param)

        # Validation step: after removing params, are there
        # any single `%` symbols that will confuse psycopg2?
        without_params = cls.extract_re.sub("", sql)
        without_double_percents = without_params.replace("%%", "")
        if "%" in without_double_percents:
            raise ValueError(r"Found a single % character")
                
        # Read values form sources
        for param in target:
            for source in value_sources:
                if param.name in source:
                    param.value = source[param.name]
                    break

        return target
    
    @classmethod
    def execute(cls, cursor, sql: str, parameters: list=[]):
        values = { param.name: param.value for param in parameters }
        cursor.execute(sql, values)

PARAMETER_CLASS = getattr(settings, "DASHBOARD_PARAMETER_CLASS", Parameter)
if isinstance(PARAMETER_CLASS, str):
    from importlib import import_module

    [module_name, class_name] = PARAMETER_CLASS.rsplit('.', 1)
    PARAMETER_CLASS = getattr(import_module(module_name), class_name)
