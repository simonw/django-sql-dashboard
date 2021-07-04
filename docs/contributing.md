# Contributing

To contribute to this library, first checkout the code. Then create a new virtual environment:

    cd django-sql-dashboard
    python -m venv venv
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

## Using Docker Compose

If you're familiar with Docker--or even if you're not--you may want to consider using our optional Docker Compose setup.

An advantage of this approach is that it relieves you of setting up any dependencies, such as ensuring that you have the proper version of Python and Postgres and so forth.  On the downside, however, it does require you to familiarize yourself with Docker, which, while relatively easy to use, still has its own learning curve.

To try out the Docker Compose setup, you will first want to [get Docker][] and [install Docker Compose][].

Then, after checking out the code, run the following:

```
cd django-sql-dashboard
docker-compose build
```

At this point, you can start editing code.  To run any development tools such as `pytest` or `black`, just prefix everything with `docker-compose run app`.  For instance, to run the test suite, run:

```
docker-compose run app python pytest
```

If this is a hassle, you can instead run a bash shell inside your container:

```
docker-compose run app bash
```

At this point, you'll be in a bash shell inside your container, and can run development tools directly.

[get Docker]: https://docs.docker.com/get-docker/
[install Docker Compose]: https://docs.docker.com/compose/install/

### Using the dashboard interactively

The Docker Compose setup is configured to run a simple test project that you can use to tinker with the dashboard interactively.

To use it, run:

```
docker-compose up
```

Then, in a separate terminal, run:

```
docker-compose run app python test_project/manage.py createsuperuser
```

You will now be prompted to enter details about a new superuser. Once you've done that, you can visit the example app's dashboard at http://localhost:8000/.  After entering the credentials for the superuser you just created, you will be able to tinker with the dashboard.

### Editing the documentation

Running `docker-compose up` also starts the documentation system's live preview server.  You can visit it at http://localhost:8001/.

### Changing the default ports

If you are already using ports 8000 and/or 8001 for other things, you can change them.  To do this, create a file in the repository root called `.env` and populate it with the following:

```
APP_PORT=9000
DOCS_PORT=9001
```

You can change the above port values to whatever makes sense for your setup.

Once you next run `docker-compose up` again, the services will be running on the ports you specified in `.env`.

### Changing the default UID and GID

The default settings assume that the user id (UID) and group id (GID) of the account you're using to develop are both 1000.  This is likely to be the case, since that's the UID/GID of the first non-root account on most systems.  However, if your account doesn't match this, you can customize the container to use a different UID/GID.

For instance, if your UID and GID are 1001, you can build your container with the following arguments:

```
docker-compose build --build-arg UID=1001 --build-arg GID=1001
```

### Updating

The project's Python dependencies are all baked into the container image, which means that whenever they change (or to be safe, whenever you `git pull` new changes to the codebase), you will want to run:

```
docker-compose build
```

You will also want to restart `docker-compose up`.

### Cleaning up

If you somehow get your Docker Compose setup into a broken state, or you decide that you never use Docker Compose again, you can clean everything up by running:

```
docker-compose down -v
```
