from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("master/", views.master_view, name="master"),
    path("about/", views.about_view, name="about"),
    path("support/", views.support_view, name="support"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("api/import-leads/", views.import_leads, name="import_leads"),
]
