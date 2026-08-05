from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("master/", views.master_view, name="master"),
    path("diagnostic/", views.diagnostic, name="diagnostic"),
    path("api/import-leads/", views.import_leads, name="import_leads"),
]
