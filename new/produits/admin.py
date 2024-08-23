from django.contrib import admin

from .models import Product, Category, VerificationArchive, ListProductVerificationArchive

admin.site.register(Product)
admin.site.register(VerificationArchive)
admin.site.register(ListProductVerificationArchive)
admin.site.register(Category)
