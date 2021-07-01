from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Dashboard(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(blank=True, max_length=128)
    description = models.TextField(
        blank=True, help_text="Optional description (Markdown allowed)"
    )
    owned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_dashboards",
        help_text="User who owns this dashboard",
    )
    created_at = models.DateTimeField(default=timezone.now)

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
        help_text="Who can view this dashboard",
    )
    edit_policy = models.CharField(
        max_length=10,
        choices=EditPolicies.choices,
        default=EditPolicies.PRIVATE,
        help_text="Who can edit this dashboard",
    )
    view_group = models.ForeignKey(
        "auth.Group",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="can_view_dashboards",
        help_text="Group that can view, for 'Users in group' policy",
    )
    edit_group = models.ForeignKey(
        "auth.Group",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="can_edit_dashboards",
        help_text="Group that can edit, for 'Users in group' policy",
    )

    def __str__(self):
        return self.title or self.slug

    def view_summary(self):
        s = self.get_view_policy_display()
        if self.view_policy == "group":
            s += ' "{}"'.format(self.view_group)
        return s

    def get_absolute_url(self):
        return reverse("django_sql_dashboard-dashboard", args=[self.slug])

    def get_edit_url(self):
        return reverse("admin:django_sql_dashboard_dashboard_change", args=(self.id,))

    class Meta:
        permissions = [("execute_sql", "Can execute arbitrary SQL queries")]

    def user_can_edit(self, user):
        if not user:
            return False
        if self.owned_by == user:
            return True
        if self.edit_policy == self.EditPolicies.LOGGEDIN:
            return True
        if self.edit_policy == self.EditPolicies.STAFF and user.is_staff:
            return True
        if self.edit_policy == self.EditPolicies.SUPERUSER and user.is_superuser:
            return True
        if (
            self.edit_policy == self.EditPolicies.GROUP
            and self.edit_group
            and self.edit_group.user_set.filter(pk=user.pk).exists()
        ):
            return True
        return False

    @classmethod
    def get_editable_by_user(cls, user):
        allowed_policies = [cls.EditPolicies.LOGGEDIN]
        if user.is_staff:
            allowed_policies.append(cls.EditPolicies.STAFF)
        if user.is_superuser:
            allowed_policies.append(cls.EditPolicies.SUPERUSER)
        return (
            cls.objects.filter(
                models.Q(owned_by=user)
                | models.Q(edit_policy__in=allowed_policies)
                | models.Q(edit_policy=cls.EditPolicies.GROUP, edit_group__user=user)
            )
        ).distinct()

    @classmethod
    def get_visible_to_user(cls, user):
        allowed_policies = [cls.ViewPolicies.PUBLIC, cls.ViewPolicies.LOGGEDIN]
        if user.is_staff:
            allowed_policies.append(cls.ViewPolicies.STAFF)
        if user.is_superuser:
            allowed_policies.append(cls.ViewPolicies.SUPERUSER)
        return (
            cls.objects.filter(
                models.Q(owned_by=user)
                | models.Q(view_policy__in=allowed_policies)
                | models.Q(view_policy=cls.ViewPolicies.GROUP, view_group__user=user)
            )
            .annotate(
                is_owner=models.ExpressionWrapper(
                    models.Q(owned_by__exact=user.pk),
                    output_field=models.BooleanField(),
                )
            )
            .order_by("-is_owner", "slug")
        ).distinct()


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
