from django.core.management.base import CommandError

from geostore.models import Layer


class LayerCommandMixin(object):
    def _get_layer_by_pk(self, layer_pk):
        try:
            layer = Layer.objects.get(pk=layer_pk)
        except Layer.DoesNotExist:
            raise CommandError(f"Layer with pk {layer_pk} doesn't exist")
        return layer

    def _get_layer_by_name(self, name):
        try:
            return Layer.objects.get(name=name)
        except Layer.DoesNotExist:
            raise CommandError(f"Layer with name {name} doesn't exist")
