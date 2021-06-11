# Normally test_project is used as scaffolding for
# django_sql_dashboard's automated tests. However, it can
# be useful during development to have a sample project to
# tinker with interactively. These Django settings can be
# useful when we want to do that.

from .settings import *

# Just have our dashboard use the exact same credentials for
# our database, there's no need to bother with read-only
# permissions when using test_project interactively.
DATABASES["dashboard"] = DATABASES["default"]
