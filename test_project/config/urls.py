from django.contrib import admin
from django.urls import path, include

import django_sql_dashboard

urlpatterns = [
    path("dashboard/", include(django_sql_dashboard.urls)),
    path("admin/", admin.site.urls),
]
