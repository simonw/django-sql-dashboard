import binascii
import json
import urllib.parse
from collections import namedtuple

from django.core import signing

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
                cell = json.dumps(cell)
            fixed_row.append(cell)
        fixed.append(fixed_row)
    return fixed


class _CaptureDict:
    def __init__(self):
        self.accessed = []

    def __getitem__(self, key):
        if key not in self.accessed:
            self.accessed.append(key)
        return ""


def extract_named_parameters(sql):
    capture = _CaptureDict()
    sql % capture
    return capture.accessed


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
