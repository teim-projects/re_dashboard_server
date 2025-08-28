 
# Create your models here.
from django.db import models

class UploadMetadata(models.Model):
    table_name = models.CharField(max_length=255, unique=True)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.table_name} - {self.last_modified}"
