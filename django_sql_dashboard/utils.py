import json

SQL_SALT = "django_sql_dashboard:query"


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
