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
    raw_id_fields = ("created_by",)
    readonly_fields = ("created_at",)
    fieldsets = (
        (
            None,
            {"fields": ("slug", "title", "description", "created_by", "created_at")},
        ),
        (
            "Permissions",
            {"fields": ("view_policy", "edit_policy", "view_group", "edit_group")},
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        obj.save()
