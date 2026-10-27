from django.urls import path

from . import views

app_name = "weiss"

urlpatterns = [
    path("", views.set_list, name="sets"),
    path("sets/<int:expansion_id>/", views.set_detail, name="set"),
    path("cards/<int:pk>/", views.card_detail, name="card"),
]
