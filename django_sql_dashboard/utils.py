from collections import namedtuple
import json

SQL_SALT = "django_sql_dashboard:query"


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


def displayable_rows(rows, columns):
    fixed = []
    for row in rows:
        fixed_row = []
        for cell in row:
            if isinstance(cell, (dict, list)):
                cell = json.dumps(cell)
            fixed_row.append(cell)
        fixed.append(dict(zip(columns, fixed_row)))
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
