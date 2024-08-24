from django.contrib import admin
from .models import CustomUser, CustomGroup, MyLogEntry, cordinates
admin.site.register(CustomUser)
admin.site.register(MyLogEntry)
admin.site.register(CustomGroup)
admin.site.register(cordinates)
# Register your models here.