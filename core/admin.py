from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "s3_key", "is_active", "created")
    list_filter = ("is_active",)
