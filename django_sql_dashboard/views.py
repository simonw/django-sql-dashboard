from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse


@staff_member_required
def dashboard(request):
    return HttpResponse("<title>Django SQL Dashboard</title>")
