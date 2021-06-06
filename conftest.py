import pytest
from django.contrib.auth.models import Permission

from django_sql_dashboard.models import Dashboard


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


@pytest.fixture
def saved_dashboard(dashboard_db):
    dashboard = Dashboard.objects.create(
        slug="test",
        title="Test dashboard",
        description="This [supports markdown](http://example.com/)",
        view_policy="public",
    )
    dashboard.queries.create(sql="select 11 + 33")
    dashboard.queries.create(sql="select 22 + 55")
    return dashboard
