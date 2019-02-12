import argparse
import json
from json.decoder import JSONDecodeError

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _

from terracommon.terra.models import Layer
from terracommon.terra.tiles.helpers import guess_maxzoom, guess_minzoom


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('-pk', '--layer-pk',
                            type=int,
                            action="store",
                            required=True,
                            help=_("PK of the layer to update"))
        parser.add_argument('-l', '--layer',
                            action="store",
                            help=("Change the name of the layer"))
        parser.add_argument('-ls', '--layer_settings', nargs='?',
                            type=argparse.FileType('r'),
                            action="store",
                            help=("Replace JSON settings file to override default"))
        parser.add_argument('-gr', '--group',
                            action="store",
                            help=_("Group name of the created layer"))
        parser.add_argument('-gz', '--guess_zoom',
                            action='store_true',
                            help=_("Guess min and max zoom from data"))

    def handle(self, *args, **options):
        layer_pk = options.get('layer_pk')
        try:
            layer = Layer.objects.get(pk=layer_pk)
        except Layer.DoesNotExist:
            raise CommandError("Please provide a valid layer pk")

        self._settings(layer, options)
        self._actions(layer, options)
        layer.save()

    def _settings(self, layer, options):
        layer_name = options.get('layer')
        group = options.get('group')

        if layer_name:
            layer.name = layer_name
        if group:
            layer.group = group

        layer_settings = options.get('layer_settings')
        if layer_settings:
            self._settings_settings(layer, layer_settings)

    def _settings_settings(self, layer, layer_settings):
        try:
            layer.settings = json.loads(layer_settings.read())
        except (JSONDecodeError, UnicodeDecodeError):
            raise CommandError("Please provide a valid layer settings file")

    def _actions(self, layer, options):
        guess_zoom = options.get('guess_zoom')

        if guess_zoom:
            layer.set_layer_settings('tiles', 'minzoom', guess_minzoom(layer))
            layer.set_layer_settings('tiles', 'maxzoom', guess_maxzoom(layer))
