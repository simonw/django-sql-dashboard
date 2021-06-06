import pytest
import pathlib
import re

docs_dir = pathlib.Path(__file__).parent.parent / "docs"
widgets_md = (docs_dir / "widgets.md").read_text()
widget_templates_dir = (
    pathlib.Path(__file__).parent.parent
    / "django_sql_dashboard"
    / "templates"
    / "django_sql_dashboard"
    / "widgets"
)
header_re = re.compile(r"^## (.*)", re.M)
headers = [
    bit.split(":")[-1].strip().replace(", ", "-")
    for bit in header_re.findall(widgets_md)
]


@pytest.mark.parametrize(
    "template",
    [
        t
        for t in widget_templates_dir.glob("*.html")
        if t.stem not in ("default", "error") and not t.stem.startswith("_")
    ],
)
def test_widgets_are_documented(template):
    assert template.stem in headers, "Widget {} is not documented".format(template.stem)
