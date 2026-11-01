"""Service instance registry views."""

import json
import uuid
from django.utils import timezone
from django.http import JsonResponse, HttpResponseBadRequest
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import ServiceInstance


def _parse_body(request):
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, AttributeError, UnicodeDecodeError):
        return {}


@method_decorator(csrf_exempt, name='dispatch')
class HealthView(View):
    def get(self, request):
        return JsonResponse({'status': 'ok', 'service': 'discovery-service'})


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(View):
    """Register a service instance.

    POST /register
    body: { service_name, host, port, metadata? }
    """

    def post(self, request):
        data = _parse_body(request)
        service_name = data.get('service_name')
        host = data.get('host')
        port = data.get('port')
        metadata = data.get('metadata', {})

        if not service_name or not host or port is None:
            return HttpResponseBadRequest(
                JsonResponse({'error': 'service_name, host and port are required'}, status=400)
            )

        instance_id = data.get('instance_id') or f'{service_name}-{uuid.uuid4().hex[:8]}'

        instance, created = ServiceInstance.objects.update_or_create(
            instance_id=instance_id,
            defaults={
                'service_name': service_name,
                'host': host,
                'port': int(port),
                'status': ServiceInstance.STATUS_UP,
                'metadata': metadata,
                'last_heartbeat': timezone.now(),
            },
        )
        return JsonResponse({
            'instance_id': instance.instance_id,
            'service_name': instance.service_name,
            'host': instance.host,
            'port': instance.port,
            'status': instance.status,
            'registered': created,
        })


@method_decorator(csrf_exempt, name='dispatch')
class HeartbeatView(View):
    """Refresh the heartbeat of a service instance.

    POST /heartbeat/<instance_id>/
    """

    def post(self, request, instance_id):
        try:
            instance = ServiceInstance.objects.get(instance_id=instance_id)
        except ServiceInstance.DoesNotExist:
            return JsonResponse({'error': 'instance not found'}, status=404)

        instance.status = ServiceInstance.STATUS_UP
        instance.last_heartbeat = timezone.now()
        instance.save(update_fields=['status', 'last_heartbeat'])
        return JsonResponse({
            'instance_id': instance.instance_id,
            'status': instance.status,
            'last_heartbeat': instance.last_heartbeat.isoformat(),
        })


@method_decorator(csrf_exempt, name='dispatch')
class DeregisterView(View):
    """Deregister a service instance.

    DELETE /deregister/<instance_id>/
    """

    def delete(self, request, instance_id):
        deleted, _ = ServiceInstance.objects.filter(instance_id=instance_id).delete()
        if not deleted:
            return JsonResponse({'error': 'instance not found'}, status=404)
        return JsonResponse({'instance_id': instance_id, 'deregistered': True})


class ServiceInstancesView(View):
    """List live instances of a service.

    GET /services/<service_name>/
    """

    def get(self, request, service_name):
        instances = ServiceInstance.objects.filter(service_name=service_name)
        alive = [i for i in instances if i.is_alive()]
        return JsonResponse({
            'service_name': service_name,
            'count': len(alive),
            'instances': [
                {
                    'instance_id': i.instance_id,
                    'host': i.host,
                    'port': i.port,
                    'url': i.url,
                    'status': i.status,
                    'last_heartbeat': i.last_heartbeat.isoformat(),
                    'metadata': i.metadata,
                }
                for i in alive
            ],
        })


class AllServicesView(View):
    """List all registered services.

    GET /services/
    """

    def get(self, request):
        from django.db.models import Max
        services = (
            ServiceInstance.objects.values('service_name')
            .annotate(last_heartbeat=Max('last_heartbeat'))
            .order_by('service_name')
        )
        return JsonResponse({'services': list(services)})
