"""Users app URLs."""

from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.HealthView.as_view(), name='health'),
    path('patients/', views.PatientListView.as_view(), name='patient-list'),
    path('patients/<int:patient_id>/', views.PatientDetailView.as_view(), name='patient-detail'),
]
