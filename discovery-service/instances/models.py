"""Service instance registry models."""

from django.db import models


class ServiceInstance(models.Model):
    """A registered microservice instance with heartbeat tracking."""

    STATUS_UP = 'UP'
    STATUS_DOWN = 'DOWN'
    STATUS_CHOICES = [
        (STATUS_UP, 'Up'),
        (STATUS_DOWN, 'Down'),
    ]

    instance_id = models.CharField(max_length=100, unique=True)
    service_name = models.CharField(max_length=100, db_index=True)
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_UP)
    last_heartbeat = models.DateTimeField(auto_now=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['service_name', 'instance_id']
        unique_together = [['service_name', 'host', 'port']]

    def __str__(self):
        return f'{self.service_name}/{self.instance_id} ({self.host}:{self.port})'

    @property
    def url(self):
        return f'http://{self.host}:{self.port}'

    def is_alive(self, threshold_seconds=30):
        from django.utils import timezone
        delta = (timezone.now() - self.last_heartbeat).total_seconds()
        return delta <= threshold_seconds
