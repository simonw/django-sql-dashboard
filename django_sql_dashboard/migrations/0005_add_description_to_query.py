# Generated by Django 3.2.8 on 2023-04-14 16:44

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("django_sql_dashboard", "0004_add_description_help_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="dashboardquery",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="dashboardquery",
            name="description",
            field=models.TextField(
                blank=True, help_text="Optional description (Markdown allowed)"
            ),
        ),
        migrations.AddField(
            model_name="dashboardquery",
            name="settings",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Settings for this query (JSON). These settings are passed to the template.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="dashboardquery",
            name="template",
            field=models.CharField(
                blank=True,
                help_text="Template to use for rendering this query. Leave blank to use the default template or fetch based on the column names.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="dashboardquery",
            name="title",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AlterField(
            model_name="dashboardquery",
            name="sql",
            field=models.TextField(verbose_name="SQL query"),
        ),
    ]
