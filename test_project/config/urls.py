from django.contrib import admin
from django.http import HttpResponse
from django.urls import path

from django_sql_dashboard.views import dashboard, dashboard_index

urlpatterns = [
    path("dashboard/", dashboard_index, name="django_sql_dashboard-index"),
    path("dashboard/<slug>/", dashboard),
    path("admin/", admin.site.urls),
]
