from django.urls import path

from . import lists, views

app_name = "weiss"

urlpatterns = [
    path("", views.set_list, name="sets"),
    path("sets/<int:expansion_id>/", views.set_detail, name="set"),
    path("cards/<int:pk>/", views.card_detail, name="card"),
    path("lists/", lists.list_index, name="lists"),
    path("lists/new/", lists.list_create, name="list_create"),
    path("lists/stop-editing/", lists.list_stop_editing, name="list_stop_editing"),
    path("lists/<int:pk>/", lists.list_detail, name="list"),
    path("lists/<int:pk>/edit/", lists.list_edit, name="list_edit"),
    path("lists/<int:pk>/cards/", lists.list_change, name="list_change"),
    path("lists/<int:pk>/rename/", lists.list_rename, name="list_rename"),
    path("lists/<int:pk>/delete/", lists.list_delete, name="list_delete"),
]
