from django.db import models
from django.utils import timezone
from django.conf import settings


class Dashboard(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(blank=True, max_length=128)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_dashboards",
    )
    created_at = models.DateTimeField(default=timezone.now())

    class ViewPolicies(models.TextChoices):
        PRIVATE = ("private", "Private")
        PUBLIC = ("public", "Public")
        UNLISTED = ("unlisted", "Unlisted")
        LOGGEDIN = ("loggedin", "Logged-in users")
        GROUP = ("group", "Users in group")
        STAFF = ("staff", "Staff users")
        SUPERUSER = ("superuser", "Superusers")

    class EditPolicies(models.TextChoices):
        PRIVATE = ("private", "Private")
        LOGGEDIN = ("loggedin", "Logged-in users")
        GROUP = ("group", "Users in group")
        STAFF = ("staff", "Staff users")
        SUPERUSER = ("superuser", "Superusers")

    # Permissions
    view_policy = models.CharField(
        max_length=10,
        choices=ViewPolicies.choices,
        default=ViewPolicies.PRIVATE,
    )
    edit_policy = models.CharField(
        max_length=10,
        choices=EditPolicies.choices,
        default=EditPolicies.PRIVATE,
    )
    view_group = models.ForeignKey(
        "auth.Group",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="can_view_dashboards",
    )
    edit_group = models.ForeignKey(
        "auth.Group",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="can_edit_dashboards",
    )

    def __str__(self):
        return self.slug

    class Meta:
        permissions = [("execute_sql", "Can execute arbitrary SQL queries")]


class DashboardQuery(models.Model):
    dashboard = models.ForeignKey(
        Dashboard, related_name="queries", on_delete=models.CASCADE
    )
    sql = models.TextField()

    def __str__(self):
        return self.sql

    class Meta:
        verbose_name_plural = "Dashboard queries"
        order_with_respect_to = "dashboard"
