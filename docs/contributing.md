# Contributing

To contribute to this library, first checkout the code. Then create a new virtual environment:

    cd django-sql-dashboard
    python -mvenv venv
    source venv/bin/activate

Or if you are using `pipenv`:

    pipenv shell

Now install the dependencies and tests:

    pip install -e '.[test]'

## Running the tests

To run the tests:

    pytest

## Generating new migrations

To generate migrations for model changes:

    cd test_project
    ./manage.py makemigrations

## Code style

This library uses [Black](https://github.com/psf/black) for code formatting.
