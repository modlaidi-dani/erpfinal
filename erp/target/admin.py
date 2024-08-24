from django.contrib import admin

# Register your models here.
from .models import Target, TargetProduct

admin.site.register(Target)
admin.site.register(TargetProduct)