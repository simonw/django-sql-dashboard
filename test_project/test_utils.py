import pytest

from django_sql_dashboard.utils import is_valid_base64_json


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
