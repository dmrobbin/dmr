from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("download/<int:pk>/", views.download, name="download"),
    path("view/<int:pk>/", views.view_document, name="view_document"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/leads/<int:pk>/", views.lead_detail, name="lead_detail"),
    path("dashboard/leads/<int:pk>/file/", views.lead_file, name="lead_file"),
    path("dashboard/leads/<int:pk>/applied/", views.lead_applied, name="lead_applied"),
    path("dashboard/leads/<int:pk>/upload/", views.lead_upload, name="lead_upload"),
]
