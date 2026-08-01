from django.urls import path

from .mcp import mcp_endpoint
from .views import dashboard, dashboard_json, dashboard_index

urlpatterns = [
    path("", dashboard_index, name="django_sql_dashboard-index"),
    path("-/mcp", mcp_endpoint, name="django_sql_dashboard-mcp"),
    path("<slug>/", dashboard, name="django_sql_dashboard-dashboard"),
    path("<slug>.json", dashboard_json, name="django_sql_dashboard-dashboard_json"),
]
