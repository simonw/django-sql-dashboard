from django.db import models


class Switch(models.Model):
    name = models.SlugField()
    on = models.BooleanField(default=False)

    class Meta:
        db_table = "switches"
