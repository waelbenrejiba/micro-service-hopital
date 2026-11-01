"""User-service views: health + patients API."""

import json
import threading
import time
import requests
from django.http import JsonResponse, HttpResponseBadRequest
from django.views import View
from django.utils import timezone
from django.conf import settings

from .models import Patient


class HealthView(View):
    def get(self, request):
        return JsonResponse({'status': 'ok', 'service': settings.SERVICE_NAME})


class PatientListView(View):
    def get(self, request):
        patients = Patient.objects.all()
        return JsonResponse({
            'count': patients.count(),
            'patients': [
                {
                    'id': p.id,
                    'full_name': p.full_name,
                    'first_name': p.first_name,
                    'last_name': p.last_name,
                    'date_of_birth': p.date_of_birth.isoformat(),
                    'gender': p.gender,
                    'phone': p.phone,
                    'email': p.email,
                    'created_at': p.created_at.isoformat(),
                }
                for p in patients
            ],
        })

    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return HttpResponseBadRequest(JsonResponse({'error': 'invalid json'}, status=400))

        required = ['first_name', 'last_name', 'date_of_birth', 'gender']
        missing = [k for k in required if not data.get(k)]
        if missing:
            return HttpResponseBadRequest(
                JsonResponse({'error': 'missing fields', 'missing': missing}, status=400)
            )

        patient = Patient.objects.create(
            first_name=data['first_name'],
            last_name=data['last_name'],
            date_of_birth=data['date_of_birth'],
            gender=data['gender'],
            phone=data.get('phone', ''),
            email=data.get('email', ''),
        )
        return JsonResponse({
            'id': patient.id,
            'full_name': patient.full_name,
            'created': True,
        }, status=201)


class PatientDetailView(View):
    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return JsonResponse({'error': 'patient not found'}, status=404)
        return JsonResponse({
            'id': patient.id,
            'full_name': patient.full_name,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'date_of_birth': patient.date_of_birth.isoformat(),
            'gender': patient.gender,
            'phone': patient.phone,
            'email': patient.email,
        })


# ---------------------------------------------------------------------------
# Startup bootstrap: fetch config, register with discovery, heartbeat loop
# ---------------------------------------------------------------------------

_bootstrapped = False


def _fetch_config():
    """Retrieve configuration (+ secrets) from the config service at startup."""
    config_url = getattr(settings, 'CONFIG_URL', 'http://localhost:8002')
    service_name = getattr(settings, 'SERVICE_NAME', 'user-service')
    env = getattr(settings, 'ENV', 'dev')
    url = f'{config_url.rstrip("/")}/configs/{service_name}/{env}/'
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get('config', {})
    except requests.RequestException as exc:
        # Config service unavailable at startup: keep running with defaults.
        print(f'[user-service] config fetch failed: {exc}')
        return {}


def _register():
    """Register this instance with the service discovery registry."""
    discovery_url = getattr(settings, 'DISCOVERY_URL', 'http://localhost:8001')
    service_name = getattr(settings, 'SERVICE_NAME', 'user-service')
    host = getattr(settings, 'SERVICE_HOST', 'localhost')
    port = getattr(settings, 'SERVICE_PORT', 8003)
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
        print(f'[user-service] registered with discovery: {resp.json()}')
    except requests.RequestException as exc:
        print(f'[user-service] registration failed: {exc}')


def _heartbeat_loop():
    """Periodically heartbeat to the discovery registry."""
    discovery_url = getattr(settings, 'DISCOVERY_URL', 'http://localhost:8001')
    service_name = getattr(settings, 'SERVICE_NAME', 'user-service')
    host = getattr(settings, 'SERVICE_HOST', 'localhost')
    port = getattr(settings, 'SERVICE_PORT', 8003)
    instance_id = f'{service_name}-{host}-{port}'
    url = f'{discovery_url.rstrip("/")}/heartbeat/{instance_id}/'
    while True:
        time.sleep(15)
        try:
            requests.post(url, timeout=5)
        except requests.RequestException:
            # Best-effort; registration will be re-attempted on restart.
            pass


def bootstrap():
    """Run once at startup: fetch config, register, start heartbeat thread."""
    global _bootstrapped
    if _bootstrapped:
        return
    _bootstrapped = True

    config = _fetch_config()
    if config:
        print(f'[user-service] config loaded: {list(config.keys())}')

    _register()

    t = threading.Thread(target=_heartbeat_loop, daemon=True)
    t.start()
