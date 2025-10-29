from django.db import models

# Create your models here.
from django.db import models

class ChargeMaster(models.Model):
    """Stores fixed charge rates (annual or standard) for Open Access Calculator."""
    name = models.CharField(max_length=100, unique=True)
    value = models.FloatField()
    unit = models.CharField(max_length=50, blank=True, null=True)
    year = models.IntegerField(default=2025)
    energy_type = models.CharField(max_length=50, blank=True, null=True)  # ✅ NEW FIELD
    updated_at = models.DateTimeField(auto_now=True)
    state = models.CharField(max_length=50, blank=True, null=True)  # ✅ Ensure this exists


    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.value} {self.unit or ''}"

# models.py

from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.db import models

class OpenAccessCalculation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    energy_type = models.CharField(max_length=50, blank=True, null=True)  # ✅ new field
    msedcl_total = models.FloatField()
    oa_total = models.FloatField()
    blended_rate = models.FloatField()
    savings = models.FloatField()
    calc_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.energy_type or 'N/A'} - {self.calc_date.strftime('%Y-%m-%d %H:%M')}"
