from django.contrib import admin
from django.http import HttpResponse
from django.urls import path

from django_sql_dashboard.views import dashboard

urlpatterns = [
    path("dashboard", dashboard),
    path("admin/", admin.site.urls),
    path("200", lambda request: HttpResponse("Status 200")),
]
