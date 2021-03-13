from django.urls import path
from django.http import HttpResponse

urlpatterns = [
    path("200", lambda request: HttpResponse("Status 200")),
]
