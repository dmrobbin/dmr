from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html

from .models import Document, Invitation, JobLead, JobSearch


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


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    """Create a single-use signup link for someone who should only see the Weiss card pages."""

    list_display = ("__str__", "status", "expires_at", "user", "created")
    fields = ("note", "expires_at", "invite_link", "status", "user", "accepted_at", "created_by", "created")
    readonly_fields = ("invite_link", "status", "user", "accepted_at", "created_by", "created")

    def get_readonly_fields(self, request, obj=None):
        self.request = request  # invite_link needs it to build a full URL
        return super().get_readonly_fields(request, obj)

    def link(self, request, invitation):
        return request.build_absolute_uri(reverse("accept_invitation", args=[invitation.token]))

    @admin.display(description="Invitation link")
    def invite_link(self, invitation):
        if not invitation.pk:
            return "Save to create the link."
        if not invitation.is_usable:
            return f"{invitation.status}; this link no longer works."
        url = self.link(self.request, invitation)
        return format_html(
            '<input type="text" value="{}" readonly size="80" onclick="this.select()" style="font-family: monospace">'
            "<p class=\"help\">Send this to the person you're inviting. It works once, until the expiry date.</p>",
            url,
        )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        messages.success(request, f"Invitation link (copy and send it): {self.link(request, obj)}")
        # Always land on the invitation's page, where the link is shown ready to copy.
        return redirect("admin:core_invitation_change", obj.pk)
