from django.urls import path

from . import lists, play, views

app_name = "weiss"

urlpatterns = [
    path("", views.set_list, name="sets"),
    path("sets/<int:expansion_id>/", views.set_detail, name="set"),
    path("series/<str:code>/", views.series_detail, name="series"),
    path("cards/<int:pk>/",views.card_detail, name="card"),
    path("cards/<int:pk>/popup/", views.card_popup, name="card_popup"),
    path("cards/<int:pk>/image/",views.card_image, name="card_image"),
    path("play/", play.room_list, name="play_rooms"),
    path("play/new/", play.room_create, name="play_create"),
    path("play/join/<str:token>/", play.room_join, name="play_join"),
    path("play/<int:pk>/", play.room_detail, name="play_room"),
    path("play/<int:pk>/deck/", play.room_deck, name="play_deck"),
    path("play/<int:pk>/start/", play.room_start, name="play_start"),
    path("play/<int:pk>/reset/", play.room_reset, name="play_reset"),
    path("play/<int:pk>/delete/", play.room_delete, name="play_delete"),
    path("play/<int:pk>/state/", play.room_state, name="play_state"),
    path("play/<int:pk>/action/", play.room_action, name="play_action"),
    path("lists/", lists.list_index, name="lists"),
    path("lists/new/", lists.list_create, name="list_create"),
    path("lists/stop-editing/", lists.list_stop_editing, name="list_stop_editing"),
    path("lists/<int:pk>/", lists.list_detail, name="list"),
    path("lists/<int:pk>/edit/", lists.list_edit, name="list_edit"),
    path("lists/<int:pk>/cards/", lists.list_change, name="list_change"),
    path("lists/<int:pk>/deck/", lists.list_deck, name="list_deck"),
    path("lists/<int:pk>/rename/",lists.list_rename, name="list_rename"),
    path("lists/<int:pk>/delete/", lists.list_delete, name="list_delete"),
]
