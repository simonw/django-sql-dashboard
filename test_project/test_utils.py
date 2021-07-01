import pytest

from django_sql_dashboard.utils import apply_sort, is_valid_base64_json


@pytest.mark.parametrize(
    "input,expected",
    (
        (
            "InNlbGVjdCAlKG5hbWUpcyBhcyBuYW1lLCB0b19jaGFyKGRhdGVfdHJ1bmMoJ21vbnRoJywgY3JlYXRlZCksICdZWVlZLU1NJykgYXMgYmFyX2xhYmVsLFxyXG5jb3VudCgqKSBhcyBiYXJfcXVhbnRpdHkgZnJvbSBibG9nX2VudHJ5IGdyb3VwIGJ5IGJhcl9sYWJlbCBvcmRlciBieSBjb3VudCgqKSBkZXNjIg",
            True,
        ),
        ("InNlbGVjdCAlKG5hbWUpcyBhcyBuYW1lLCB0", False),
        ("Not valid", False),
        ("InNlbGVjdCAlKG5hbWUpcyBhcyBuYW1lLCB0", False),
    ),
)
def test_is_valid_base64_json(input, expected):
    assert is_valid_base64_json(input) == expected


@pytest.mark.parametrize(
    "sql,sort_column,is_desc,expected_sql",
    (
        (
            "select * from foo",
            "bar",
            False,
            'select * from (select * from foo) as results order by "bar"',
        ),
        (
            "select * from foo",
            "bar",
            True,
            'select * from (select * from foo) as results order by "bar" desc',
        ),
        (
            'select * from (select * from foo) as results order by "bar" desc',
            "bar",
            False,
            'select * from (select * from foo) as results order by "bar"',
        ),
        (
            'select * from (select * from foo) as results order by "bar"',
            "bar",
            True,
            'select * from (select * from foo) as results order by "bar" desc',
        ),
    ),
)
def test_apply_sort(sql, sort_column, is_desc, expected_sql):
    assert apply_sort(sql, sort_column, is_desc) == expected_sql
