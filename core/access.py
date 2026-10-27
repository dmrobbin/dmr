"""Who can see which part of the dashboard.

Staff see everything. Members of the "Weiss users" group (people who signed up through an
invitation) see only the Weiss Schwarz card pages.
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login

WEISS_GROUP = "Weiss users"


def has_weiss_access(user):
    return user.is_authenticated and user.is_active and (
        user.is_staff or user.groups.filter(name=WEISS_GROUP).exists()
    )


def weiss_access_required(view):
    """Like staff_member_required, but also lets Weiss users in; everyone else goes to the login page."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if has_weiss_access(request.user):
            return view(request, *args, **kwargs)
        return redirect_to_login(request.get_full_path())
    return wrapper
