import argparse
import json
import uuid

from django.core.management.base import BaseCommand
from django.db import transaction

from terracommon.terra.models import Layer


class Command(BaseCommand):
    help = 'Import Features from GeoJSON files'

    def add_arguments(self, parser):
        exclusive_group = parser.add_mutually_exclusive_group()
        exclusive_group.add_argument('-pk', '--layer-pk',
                            type=int,
                            action="store",
                            help=("PK of the layer where to insert the"
                                  "features.\n"
                                  "A new layer is created if not present"))
        exclusive_group.add_argument('-l', '--layer',
                            action="store",
                            help=("Name of created layer "
                                  "containing GeoJSON datas."
                                  "If not provided an uuid4 is set."))
        parser.add_argument('-s', '--schema',
                            type=argparse.FileType('r'),
                            action="store",
                            help=("JSON schema file that describe "
                                  "GeoJSON properties.\n"
                                  "Only needed if -l option is provided"))
        parser.add_argument('-g', '--geojson',
                            nargs='+',
                            type=argparse.FileType('r'),
                            action="store",
                            required=True,
                            help='GeoJSON files to import')
        parser.add_argument('--dry-run',
                            action="store_true",
                            help='Execute une dry-run mode')

    @transaction.atomic()
    def handle(self, *args, **options):
        layer_pk = options.get('layer_pk', None)
        layer_name = options.get('layer') if \
            options.get('layer', None) else uuid.uuid4()
        geojson_files = options.get('geojson')
        dryrun = options.get('dry_run')

        sp = transaction.savepoint()

        if layer_pk:
            layer = Layer.objects.get(pk=layer_pk)
        else:
            try:
                schema = json.loads(options.get('schema').read())
            except AttributeError:
                raise argparse.ArgumentTypeError('Please provide a valid schema file')
            layer = Layer.objects.create(name=layer_name, schema=schema)

        self.import_datas(layer, geojson_files)

        if dryrun:
            transaction.savepoint_rollback(sp)
        else:
            transaction.savepoint_commit(sp)

    def import_datas(self, layer, geojson_files):
        for file_in in geojson_files:
            geojson = file_in.read()
            layer.from_geojson(geojson)
