from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("download/<int:pk>/", views.download, name="download"),
    path("view/<int:pk>/", views.view_document, name="view_document"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
