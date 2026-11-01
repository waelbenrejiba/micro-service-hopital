"""Service instance registry URLs."""

from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.HealthView.as_view(), name='health'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('heartbeat/<str:instance_id>/', views.HeartbeatView.as_view(), name='heartbeat'),
    path('deregister/<str:instance_id>/', views.DeregisterView.as_view(), name='deregister'),
    path('services/', views.AllServicesView.as_view(), name='all-services'),
    path('services/<str:service_name>/', views.ServiceInstancesView.as_view(), name='service-instances'),
]
