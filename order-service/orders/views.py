"""Order-service views: health + orders API + startup bootstrap."""

import json
import threading
import time
import requests
from django.http import JsonResponse, HttpResponseBadRequest
from django.views import View
from django.conf import settings

from .models import Order


class HealthView(View):
    def get(self, request):
        return JsonResponse({'status': 'ok', 'service': settings.SERVICE_NAME})


class OrderListView(View):
    def get(self, request):
        orders = Order.objects.all()
        return JsonResponse({
            'count': orders.count(),
            'orders': [
                {
                    'id': o.id,
                    'patient_name': o.patient_name,
                    'description': o.description,
                    'amount': str(o.amount),
                    'status': o.status,
                    'created_at': o.created_at.isoformat(),
                }
                for o in orders
            ],
        })

    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return HttpResponseBadRequest(JsonResponse({'error': 'invalid json'}, status=400))

        required = ['patient_name', 'description', 'amount']
        missing = [k for k in required if not data.get(k)]
        if missing:
            return HttpResponseBadRequest(
                JsonResponse({'error': 'missing fields', 'missing': missing}, status=400)
            )

        order = Order.objects.create(
            patient_name=data['patient_name'],
            description=data['description'],
            amount=data['amount'],
            status=data.get('status', 'pending'),
        )
        return JsonResponse({
            'id': order.id,
            'patient_name': order.patient_name,
            'status': order.status,
            'created': True,
        }, status=201)


class OrderDetailView(View):
    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return JsonResponse({'error': 'order not found'}, status=404)
        return JsonResponse({
            'id': order.id,
            'patient_name': order.patient_name,
            'description': order.description,
            'amount': str(order.amount),
            'status': order.status,
        })


# ---------------------------------------------------------------------------
# Startup bootstrap: fetch config, register with discovery, heartbeat loop
# ---------------------------------------------------------------------------

_bootstrapped = False


def _fetch_config():
    config_url = getattr(settings, 'CONFIG_URL', 'http://localhost:8002')
    service_name = getattr(settings, 'SERVICE_NAME', 'order-service')
    env = getattr(settings, 'ENV', 'dev')
    url = f'{config_url.rstrip("/")}/configs/{service_name}/{env}/'
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get('config', {})
    except requests.RequestException as exc:
        print(f'[order-service] config fetch failed: {exc}')
        return {}


def _register():
    discovery_url = getattr(settings, 'DISCOVERY_URL', 'http://localhost:8001')
    service_name = getattr(settings, 'SERVICE_NAME', 'order-service')
    host = getattr(settings, 'SERVICE_HOST', 'localhost')
    port = getattr(settings, 'SERVICE_PORT', 8004)
    url = f'{discovery_url.rstrip("/")}/register/'
    payload = {
        'service_name': service_name,
        'host': host,
        'port': port,
        'instance_id': f'{service_name}-{host}-{port}',
        'metadata': {'env': getattr(settings, 'ENV', 'dev')},
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        print(f'[order-service] registered with discovery: {resp.json()}')
    except requests.RequestException as exc:
        print(f'[order-service] registration failed: {exc}')


def _heartbeat_loop():
    discovery_url = getattr(settings, 'DISCOVERY_URL', 'http://localhost:8001')
    service_name = getattr(settings, 'SERVICE_NAME', 'order-service')
    host = getattr(settings, 'SERVICE_HOST', 'localhost')
    port = getattr(settings, 'SERVICE_PORT', 8004)
    instance_id = f'{service_name}-{host}-{port}'
    url = f'{discovery_url.rstrip("/")}/heartbeat/{instance_id}/'
    while True:
        time.sleep(15)
        try:
            requests.post(url, timeout=5)
        except requests.RequestException:
            pass


def bootstrap():
    global _bootstrapped
    if _bootstrapped:
        return
    _bootstrapped = True

    config = _fetch_config()
    if config:
        print(f'[order-service] config loaded: {list(config.keys())}')

    _register()

    t = threading.Thread(target=_heartbeat_loop, daemon=True)
    t.start()
