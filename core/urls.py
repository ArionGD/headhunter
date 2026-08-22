from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("overview/", views.overview_view, name="overview"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("crm/", views.crm_view, name="crm"),
    path("master/", views.master_view, name="master"),
    path("users/", views.users_admin_view, name="users_admin"),
    path("statistics/", views.statistics_admin_view, name="stats_admin"),
    path("about/", views.about_view, name="about"),
    path("support/", views.support_view, name="support"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("api/import-leads/", views.import_leads, name="import_leads"),
]

