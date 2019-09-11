import os
import subprocess
import tempfile
import uuid
from xml.etree import ElementTree as ET

import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _

from geostore.management.commands.mixins import LayerCommandMixin
from geostore.models import Layer


class Command(LayerCommandMixin, BaseCommand):
    overpass_url = "http://overpass-api.de/api/interpreter"

    def add_arguments(self, parser):
        parser.add_argument('query', action="store",
                            help=_("Overpass query without type (out:json)"
                                   ))
        parser.add_argument('-t', '--type',
                            required=True,
                            action='store',
                            dest='type',
                            help=_('Specify type of layer'
                                   ))
        parser.add_argument('-l', '--layer',
                            action="store",
                            help=_("Name of created layer "
                                   "containing GeoJSON datas."
                                   "If not provided an uuid4 is set."
                                   ))
        parser.add_argument('-pk', '--layer-pk',
                            type=int,
                            action="store",
                            help=_("PK of the layer where to insert"
                                   "the features.\n"
                                   "A new layer is created if not "
                                   "present."
                                   ))
        parser.add_argument('-gr', '--group',
                            action="store",
                            default="__nogroup__",
                            help=_("Group name of the created layer"
                                   ))
        parser.add_argument('-i', '--identifier',
                            action="store",
                            help=_("Field in properties that will be used as "
                                   "identifier of the features, so features"
                                   " can be grouped on layer's operations"
                                   ))

    def handle(self, *args, **options):
        query = options.get('query')
        layer_name = options.get('layer') or uuid.uuid4()
        type_features = options.get('type')
        layer_pk = options.get('layer_pk')
        identifier = options.get('identifier')
        verbosity = options.get('verbosity')
        response = requests.get(self.overpass_url,
                                params={'data': query})
        try:
            ET.fromstring(response.content)
        except ET.ParseError:
            if response.status_code != 400:
                raise CommandError("Overpass didn't give any information")
            raise CommandError('The query is not valid')

        value, log_error = self.launch_cmd_ogr2ogr(response.content, type_features)

        if verbosity >= 1:
            self.stderr.write(log_error)
        if not value:
            raise CommandError('Ogr2ogr failed to create the geojson')
        if layer_pk:
            layer = self._get_layer_by_pk(layer_pk)
        else:
            settings = {
                'metadata': {
                    'attribution': '<a href=\'http://openstreetmap.org\'>OSM contributors</a>',
                    'licence': 'ODbL',
                }
            }
            layer = Layer.objects.create(name=layer_name, settings=settings)

        layer.from_geojson(value, identifier)

    def launch_cmd_ogr2ogr(self, content, type_features):
        tmp_osm = tempfile.NamedTemporaryFile(mode='w+b', delete=False)
        tmp_osm.write(content)
        tmp_osm.close()
        try:
            proc = subprocess.run(
                args=[
                    'ogr2ogr',
                    '-f', 'GeoJSON', '/vsistdout/',
                    tmp_osm.name,
                    type_features,
                    '--config', 'OSM_USE_CUSTOM_INDEXING', 'NO',
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf8',)
            value = proc.stdout
            log_error = proc.stderr
        except subprocess.CalledProcessError:
            raise CommandError("Command ogr2ogr failed")
        finally:
            os.unlink(tmp_osm.name)
        return value, log_error
