import subprocess
import tempfile
import uuid

import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _

from terracommon.terra.models import Layer


class Command(BaseCommand):
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

        response = requests.get(self.overpass_url,
                                params={'data': query})
        with tempfile.NamedTemporaryFile(mode='wb') as tmp_osm:
            tmp_osm.write(response.content)
            value = subprocess.check_output(
                ['ogr2ogr', '-f', 'GeoJSON', '/vsistdout/',
                 tmp_osm.name, type_features])
            if not value:
                msg = 'Ogr2ogr failed to create the geojson'
                raise CommandError(msg)
            if layer_pk:
                layer = Layer.objects.get(pk=layer_pk)
            else:
                layer = Layer.objects.create(name=layer_name)

            layer.from_geojson(value, identifier)
