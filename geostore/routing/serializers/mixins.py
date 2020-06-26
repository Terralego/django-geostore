from django.conf import settings
from django.urls import reverse
from rest_framework import serializers


class RoutingLayerSerializer:
    if 'geostore.routing' in settings.INSTALLED_APPS:
        routing_url = serializers.SerializerMethodField()

        def get_routing_url(self, obj):
            return reverse('layer-route', args=[obj.pk, ])
