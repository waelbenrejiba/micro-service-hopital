"""Config service API URLs."""

from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.HealthView.as_view(), name='health'),
    path('configs/<str:service_name>/<str:env>/', views.ConfigView.as_view(), name='config-detail'),
    path('configs/<str:service_name>/', views.ServiceConfigView.as_view(), name='config-service'),
]
