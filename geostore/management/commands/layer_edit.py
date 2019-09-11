import argparse
import json
from json.decoder import JSONDecodeError

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _

from geostore.management.commands.mixins import LayerCommandMixin
from geostore.models import LayerGroup
from geostore.tiles.helpers import guess_maxzoom, guess_minzoom


class Command(LayerCommandMixin, BaseCommand):

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
        parser.add_argument('-gr', '--groups',
                            nargs='+',
                            help=_("Group names of the created layer"))
        parser.add_argument('-gz', '--guess_zoom',
                            action='store_true',
                            help=_("Guess min and max zoom from data"))

    def handle(self, *args, **options):
        layer_pk = options.get('layer_pk')
        layer = self._get_layer_by_pk(layer_pk)

        self._settings(layer, options)
        self._actions(layer, options)
        layer.save()

    def _settings(self, layer, options):
        layer_name = options.get('layer')
        group_names = options.get('groups')

        if group_names:
            layer.layer_groups.clear()
            for group_name in group_names:
                group, created = LayerGroup.objects.get_or_create(name=group_name)
                group.layers.add(layer)

        if layer_name:
            layer.name = layer_name

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
