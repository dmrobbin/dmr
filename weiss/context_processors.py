from .lists import panel_context


def card_lists(request):
    """The card-list side panel's data, on Weiss pages only."""
    match = getattr(request, "resolver_match", None)
    user = getattr(request, "user", None)
    if not match or match.namespace != "weiss" or not (user and user.is_authenticated and user.is_staff):
        return {}
    return panel_context(request)
