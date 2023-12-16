from django.urls import path

from .views import dashboard, dashboard_json, dashboard_index

urlpatterns = [
    path("", dashboard_index, name="django_sql_dashboard-index"),
    path("<slug>/", dashboard, name="django_sql_dashboard-dashboard"),
    path("<slug>.json", dashboard_json, name="django_sql_dashboard-dashboard_json"),
]
