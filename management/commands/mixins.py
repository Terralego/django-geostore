from django.core.management.base import CommandError

from terracommon.terra.models import Layer


class CommandMixin(object):
    def get_layer(self, layer_pk):
        try:
            layer = Layer.objects.get(pk=layer_pk)
        except Layer.DoesNotExist:
            raise CommandError(f"Layer with pk {layer_pk} doesn't exist")
        return layer
