import pytest


@pytest.fixture(scope="session")
def django_db_modify_db_settings():
    from django.conf import settings

    settings.DATABASES["dashboard"]["OPTIONS"] = {
        "options": "-c default_transaction_read_only=on -c statement_timeout=100"
    }
