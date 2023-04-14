from django.db import models

# Create your models here.
class WarehouseManagementMethod(models.Model):
    name = models.TextField(null=False, blank=False, default="", max_length=1000)

    def __str__(self):
        return f"{self.name}"