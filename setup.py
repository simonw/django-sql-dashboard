import os

from setuptools import setup

VERSION = "0.2a0"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="django-sql-dashboard",
    description="Django app for building dashboards using raw SQL queries",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Simon Willison",
    url="https://github.com/simonw/django-sql-dashboard",
    project_urls={
        "Issues": "https://github.com/simonw/django-sql-dashboard/issues",
        "CI": "https://github.com/simonw/django-sql-dashboard/actions",
        "Changelog": "https://github.com/simonw/django-sql-dashboard/releases",
    },
    license="Apache License, Version 2.0",
    version=VERSION,
    packages=["django_sql_dashboard"],
    package_data={
        "django_sql_dashboard": [
            "templates/django_sql_dashboard/*.html",
            "migrations/*.py",
        ]
    },
    install_requires=["Django"],
    extras_require={
        "test": [
            "psycopg2",
            "pytest",
            "pytest-django",
            "pytest-pythonpath",
            "dj-database-url",
            "testing.postgresql",
        ]
    },
    tests_require=["django-sql-dashboard[test]"],
    python_requires=">=3.6",
)
