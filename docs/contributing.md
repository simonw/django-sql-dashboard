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

This library uses [Black](https://github.com/psf/black) for code formatting. The correct version of Black will be installed by `pip install -e '.[test]'` - you can run `black .` in the root directory to apply those formatting rules.

## Documentation

Documentation for this project uses [MyST](https://myst-parser.readthedocs.io/) - it is written in Markdown and rendered using Sphinx.

To build the documentation locally, run the following:

    cd docs
    pip install -r requirements.txt
    make livehtml

This will start a live preview server, using [sphinx-autobuild](https://pypi.org/project/sphinx-autobuild/).
