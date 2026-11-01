"""Users app configuration: runs bootstrap (config + registration + heartbeat) at startup."""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Users'

    def ready(self):
        from .views import bootstrap  # noqa: WPS433

        bootstrap()
