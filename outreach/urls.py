from django.urls import path
from . import views

urlpatterns = [
    path('settings/', views.outreach_settings_view, name='outreach_settings'),
    path('templates/create/', views.create_template_view, name='create_email_template'),
    path('modal/<int:lead_id>/', views.get_email_modal_view, name='get_email_modal'),
    path('send/<int:lead_id>/', views.send_direct_email_api, name='send_direct_email'),
]
