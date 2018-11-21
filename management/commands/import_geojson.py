import argparse
import json
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from terracommon.terra.models import Layer


class Command(BaseCommand):
    help = 'Import Features from GeoJSON files'

    def add_arguments(self, parser):
        exclusive_group = parser.add_mutually_exclusive_group()
        exclusive_group.add_argument('-pk', '--layer-pk',
                                     type=int,
                                     action="store",
                                     help=("PK of the layer where to insert"
                                           "the features.\n"
                                           "A new layer is created if not "
                                           "present."))
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
                            type=argparse.FileType('r', encoding='UTF-8'),
                            action="store",
                            required=True,
                            help='GeoJSON files to import')
        parser.add_argument('-i', '--identifier',
                            action="store",
                            help="Field in properties that will be used as "
                                 "identifier of the features, so features can"
                                 " be grouped on layer's operations")
        parser.add_argument('-gr', '--group',
                            action="store",
                            default="__nogroup__",
                            help="Group name of the created layer")
        parser.add_argument('--dry-run',
                            action="store_true",
                            help='Execute une dry-run mode')

    @transaction.atomic()
    def handle(self, *args, **options):
        layer_pk = options.get('layer_pk')
        layer_name = options.get('layer') or uuid.uuid4()
        geojson_files = options.get('geojson')
        dryrun = options.get('dry_run')
        group = options.get('group')
        identifier = options.get('identifier')

        sp = transaction.savepoint()

        if layer_pk:
            layer = Layer.objects.get(pk=layer_pk)
        else:
            try:
                schema = json.loads(options.get('schema').read())
            except AttributeError:
                raise CommandError("Please provide a valid schema file")
            layer = Layer.objects.create(name=layer_name,
                                         schema=schema,
                                         group=group)
            if options['verbosity'] >= 1:
                self.stdout.write(f"The created layer pk is {layer.pk}, "
                                  "it can be used to import more features"
                                  " in the same layer with different "
                                  "options")

        self.import_datas(layer, geojson_files, identifier)

        if dryrun:
            transaction.savepoint_rollback(sp)
        else:
            transaction.savepoint_commit(sp)

    def import_datas(self, layer, geojson_files, identifier):
        for file_in in geojson_files:
            geojson = file_in.read()
            layer.from_geojson(geojson, identifier)
