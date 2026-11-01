"""Orders app configuration: runs bootstrap (config + registration + heartbeat) at startup."""

from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'
    verbose_name = 'Orders'

    def ready(self):
        from .views import bootstrap  # noqa: WPS433

        bootstrap()
