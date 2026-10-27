"""Login, logout, and accepting an invitation to create a Weiss-only account."""
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .access import WEISS_GROUP, has_weiss_access
from .models import Invitation


class SiteLoginView(LoginView):
    """Login for everyone (the admin's own login page only accepts staff)."""

    template_name = "core/login.html"
    form_class = AuthenticationForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        user = self.request.user
        if user.is_staff:
            return reverse("dashboard")
        return reverse("weiss:sets") if has_weiss_access(user) else reverse("home")


class SiteLogoutView(LogoutView):
    next_page = "home"


def accept_invitation(request, token):
    invitation = get_object_or_404(Invitation, token=token)
    if not invitation.is_usable:
        return render(request, "core/invitation.html", {"invitation": invitation, "unusable": True}, status=410)
    if request.user.is_authenticated:
        return render(request, "core/invitation.html", {"invitation": invitation, "signed_in": True})

    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            # Re-check under a lock so the same link can't create two accounts.
            invitation = Invitation.objects.select_for_update().get(pk=invitation.pk)
            if not invitation.is_usable:
                return render(request, "core/invitation.html", {"invitation": invitation, "unusable": True}, status=410)
            user = form.save()
            user.groups.add(Group.objects.get_or_create(name=WEISS_GROUP)[0])
            invitation.user = user
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=["user", "accepted_at"])
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("weiss:sets")
    return render(request, "core/invitation.html", {"invitation": invitation, "form": form})
