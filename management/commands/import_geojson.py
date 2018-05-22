import argparse
import json
import uuid

from django.core.management.base import BaseCommand
from django.db import transaction

from terracommon.terra.models import Layer


class Command(BaseCommand):
    help = 'Import Features from GeoJSON files'

    def add_arguments(self, parser):
        parser.add_argument('-l', '--layer',
                            action="store",
                            help=("Name of created layer "
                                  "containing GeoJSON datas"))
        parser.add_argument('-s', '--schema',
                            type=argparse.FileType('r'),
                            action="store",
                            required=True,
                            help=("JSON schema file that describe "
                                  "GeoJSON properties"))
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

        layer_name = options.get('layer') if \
            options.get('layer', None) else uuid.uuid4()
        schema = json.loads(options.get('schema').read())
        geojson_files = options.get('geojson')
        dryrun = options.get('dry_run')

        sp = transaction.savepoint()
        self.import_datas(layer_name, schema, geojson_files)

        if dryrun:
            transaction.savepoint_rollback(sp)
        else:
            transaction.savepoint_commit(sp)

    def import_datas(self, layer_name, schema, geojson_files):
        layer = Layer.objects.create(name=layer_name, schema=schema)

        for file_in in geojson_files:
            geojson = file_in.read()
            layer.from_geojson(geojson)
