"""Gateway proxy app: discovers services and forwards requests."""

import requests
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.views import View
from django.conf import settings


class DiscoveryClient:
    """Client for the service discovery registry."""

    def __init__(self, discovery_url=None, timeout=None):
        self.discovery_url = discovery_url or getattr(settings, 'DISCOVERY_URL', 'http://localhost:8001')
        self.timeout = timeout or float(getattr(settings, 'REQUEST_TIMEOUT', 10))

    def get_instances(self, service_name):
        """Return live instances for a service."""
        url = f'{self.discovery_url.rstrip("/")}/services/{service_name}/'
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get('instances', [])
        except requests.RequestException:
            return []

    def pick_instance(self, service_name):
        instances = self.get_instances(service_name)
        if not instances:
            return None
        # Round-robin-ish: pick the first live instance
        return instances[0]


class HealthView(View):
    def get(self, request):
        return HttpResponse('{"status":"ok","service":"gateway"}', content_type='application/json')


class ProxyView(View):
    """Proxy requests to a discovered service instance.

    Matches /<service_name>/<any_path> and forwards to a live instance.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.discovery = DiscoveryClient()

    def _forward(self, request, instance, service_name, path):
        target = f'{instance["url"].rstrip("/")}/{path.lstrip("/")}'
        method = request.method.lower()
        headers = {k: v for k, v in request.headers.items()
                   if k.lower() not in ('host', 'content-length')}
        try:
            if method in ('get', 'head', 'options'):
                upstream = getattr(requests, method)(
                    target,
                    params=request.GET,
                    headers=headers,
                    timeout=self.discovery.timeout,
                    allow_redirects=False,
                )
            else:
                upstream = getattr(requests, method)(
                    target,
                    data=request.body,
                    params=request.GET,
                    headers=headers,
                    timeout=self.discovery.timeout,
                    allow_redirects=False,
                )
        except requests.RequestException as exc:
            return HttpResponse(
                f'{{"error":"upstream_unreachable","detail":"{exc}"}}',
                status=502,
                content_type='application/json',
            )

        response = HttpResponse(
            upstream.content,
            status=upstream.status_code,
            content_type=upstream.headers.get('content-type', 'application/octet-stream'),
        )
        for header in ('content-type', 'cache-control'):
            if header in upstream.headers:
                response[header] = upstream.headers[header]
        return response

    def dispatch(self, request, service_name, path):
        instance = self.discovery.pick_instance(service_name)
        if not instance:
            return HttpResponse(
                f'{{"error":"service_unavailable","service":"{service_name}"}}',
                status=503,
                content_type='application/json',
            )
        return self._forward(request, instance, service_name, path)


class ServiceListView(View):
    """List all registered services (debug/ops)."""

    def get(self, request):
        discovery = DiscoveryClient()
        try:
            resp = requests.get(
                f'{discovery.discovery_url.rstrip("/")}/services/',
                timeout=discovery.timeout,
            )
            resp.raise_for_status()
            return HttpResponse(resp.content, content_type='application/json')
        except requests.RequestException as exc:
            return HttpResponse(
                f'{{"error":"discovery_unreachable","detail":"{exc}"}}',
                status=502,
                content_type='application/json',
            )
