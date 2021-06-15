from html import escape

from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import Dashboard, DashboardQuery


class DashboardQueryInline(admin.TabularInline):
    model = DashboardQuery
    extra = 1

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        return obj.user_can_edit(request.user)

    def get_readonly_fields(self, request, obj=None):
        if not request.user.has_perm("django_sql_dashboard.execute_sql"):
            return ("sql",)
        else:
            return tuple()


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ("slug", "title", "owned_by", "view_policy", "view_dashboard")
    inlines = [
        DashboardQueryInline,
    ]
    raw_id_fields = ("owned_by",)
    fieldsets = (
        (
            None,
            {"fields": ("slug", "title", "description", "owned_by", "created_at")},
        ),
        (
            "Permissions",
            {"fields": ("view_policy", "edit_policy", "view_group", "edit_group")},
        ),
    )

    def view_dashboard(self, obj):
        return mark_safe(
            '<a href="{path}">{path}</a>'.format(path=escape(obj.get_absolute_url()))
        )

    def save_model(self, request, obj, form, change):
        if not obj.owned_by_id:
            obj.owned_by = request.user
        obj.save()

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        if request.user.is_superuser:
            return True
        return obj.user_can_edit(request.user)

    def get_readonly_fields(self, request, obj):
        readonly_fields = ["created_at"]
        if not request.user.is_superuser:
            readonly_fields.append("owned_by")
        return readonly_fields

    def get_queryset(self, request):
        if request.user.is_superuser:
            # Superusers should be able to see all dashboards.
            return super().get_queryset(request)
        # Otherwise, show only the dashboards the user has edit access to.
        return Dashboard.get_editable_by_user(request.user)
