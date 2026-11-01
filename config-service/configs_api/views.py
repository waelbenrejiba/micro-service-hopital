import json
import os
from pathlib import Path

from django.http import JsonResponse, Http404
from django.views import View

from config.settings import CONFIGS_DIR, ENV


class HealthView(View):
    def get(self, request):
        return JsonResponse({'status': 'ok', 'service': 'config-service'})


class ConfigView(View):
    

    def get(self, request, service_name, env):
        # Global config (shared by all services)
        global_path = CONFIGS_DIR / f'global.{env}.json'
        # Service-specific config
        service_path = CONFIGS_DIR / f'{service_name}.{env}.json'

        config = {}

        if global_path.exists():
            with open(global_path, 'r', encoding='utf-8') as f:
                config.update(json.load(f))

        if service_path.exists():
            with open(service_path, 'r', encoding='utf-8') as f:
                config.update(json.load(f))

        if not config:
            raise Http404(f'No configuration found for service="{service_name}" env="{env}"')

        return JsonResponse({
            'service': service_name,
            'env': env,
            'config': config,
        })


class ServiceConfigView(View):
    """Convenience endpoint using the service env from settings (dev)."""

    def get(self, request, service_name):
        return ConfigView.as_view()(request, service_name, ENV)
