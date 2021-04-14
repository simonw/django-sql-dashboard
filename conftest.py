import pytest
from django.contrib.auth.models import Permission


@pytest.fixture
def dashboard_db(settings, db):
    settings.DATABASES["dashboard"]["OPTIONS"] = {
        "options": "-c default_transaction_read_only=on -c statement_timeout=100"
    }


@pytest.fixture
def execute_sql_permission():
    return Permission.objects.get(
        content_type__app_label="django_sql_dashboard",
        content_type__model="dashboard",
        codename="execute_sql",
    )
