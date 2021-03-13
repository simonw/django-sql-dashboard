from django.contrib import admin

from .models import Dashboard, DashboardQuery


class DashboardQueryInline(admin.TabularInline):
    model = DashboardQuery
    extra = 1


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    inlines = [
        DashboardQueryInline,
    ]
