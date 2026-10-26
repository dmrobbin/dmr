from django.contrib import admin

from .models import Document, JobLead, JobSearch


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "s3_key", "is_active", "created")
    list_filter = ("is_active",)


@admin.register(JobLead)
class JobLeadAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "location", "expected_compensation", "status", "applied", "source", "created")
    list_filter = ("applied", "status", "is_remote")
    list_editable = ("status", "applied")
    search_fields = ("title", "company", "summary", "source")


@admin.register(JobSearch)
class JobSearchAdmin(admin.ModelAdmin):
    list_display = ("query", "location", "remote_only", "is_active")
    list_editable = ("remote_only", "is_active")
