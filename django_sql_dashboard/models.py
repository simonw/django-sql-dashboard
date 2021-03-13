from django.db import models


class Dashboard(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(blank=True, max_length=128)
    description = models.TextField(blank=True)

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
