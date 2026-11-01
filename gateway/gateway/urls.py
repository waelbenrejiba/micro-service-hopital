"""URL configuration for gateway project."""
from django.contrib import admin
from django.urls import path, re_path
from proxy import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', views.HealthView.as_view(), name='health'),
    path('services/', views.ServiceListView.as_view(), name='services'),
    # Catch-all proxy route: /<service_name>/<any_path>
    re_path(r'^(?P<service_name>[^/]+)/(?P<path>.*)$', views.ProxyView.as_view(), name='proxy'),
]
