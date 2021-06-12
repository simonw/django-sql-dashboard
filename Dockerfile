FROM python:3.9

WORKDIR /app

# Set up the minimum structure needed to install
# django_sql_dashboard's dependencies and the package itself
# in development mode.
COPY setup.py README.md .
RUN mkdir django_sql_dashboard && pip install -e '.[test]'

# We need to have postgres installed in this container
# because the automated test suite actually spins up
# (and shuts down) a database inside the container.
RUN apt-get update && apt-get install -y \
  postgresql postgresql-contrib \
  && rm -rf /var/lib/apt/lists/*

# Install dependencies needed for editing documentation.
COPY docs/requirements.txt .
RUN pip install -r requirements.txt

ARG GID=1000
ARG UID=1000

# Set up a non-root user.  Aside from being best practice,
# we also need to do this because the test suite refuses to
# run as the root user.
RUN groupadd -g ${GID} appuser && useradd -r -u ${UID} -g appuser appuser

USER appuser
