from django.contrib import admin
from .models import store, CompteEntreprise, typeClient

admin.site.register(store)
admin.site.register(typeClient)
admin.site.register(CompteEntreprise)
# Register your models here.
