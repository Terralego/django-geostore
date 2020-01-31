import argparse
import json
import uuid
from json.decoder import JSONDecodeError

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from geostore.management.commands.mixins import LayerCommandMixin
from geostore.models import Layer, LayerGroup, LayerSchemaProperty


class Command(LayerCommandMixin, BaseCommand):
    help = 'Import Features from GeoJSON files'

    def add_arguments(self, parser):
        parser.add_argument('file_path',
                            nargs='+',
                            type=argparse.FileType('r'),
                            action="store",
                            help='GeoJSON files to import')
        exclusive_group = parser.add_mutually_exclusive_group()
        exclusive_group.add_argument('-pk', '--layer-pk',
                                     type=int,
                                     action="store",
                                     help="PK of the layer where to insert the features."
                                          "A new layer is created if not present.")
        exclusive_group.add_argument('-ln', '--layer-name',
                                     action="store",
                                     help="Name of created layer containing GeoJSON datas."
                                          "If not provided an uuid4 is set.")
        parser.add_argument('-gs', '--generate-schema',
                            action="store_true",
                            help=("Generate json form schema from"
                                  "GeoJSON properties.\n"
                                  "Only needed if -l option is provided"))
        parser.add_argument('-ls', '--layer-settings', nargs='?',
                            type=argparse.FileType('r'),
                            action="store",
                            help=("JSON settings file to override default"))

        parser.add_argument('-i', '--identifier',
                            action="store",
                            help="Field in properties that will be used as "
                                 "identifier of the features, so features can"
                                 " be grouped on layer's operations")
        parser.add_argument('-gr', '--group',
                            action="store",
                            default="default",
                            help="Group name of the created layer")
        parser.add_argument('--dry-run',
                            action="store_true",
                            help='Execute une dry-run mode')

    @transaction.atomic()
    def handle(self, *args, **options):
        layer_pk = options.get('layer_pk')
        layer_name = options.get('layer_name') or uuid.uuid4()
        file_path = options.get('file_path')
        dryrun = options.get('dry_run')
        group_name = options.get('group')
        identifier = options.get('identifier')
        layer_settings = options.get('layer_settings')
        generate_schema = options.get('generate_schema')

        sp = transaction.savepoint()

        if layer_pk:
            layer = self._get_layer_by_pk(layer_pk)
        else:
            try:
                settings = json.loads(layer_settings.read()) if layer_settings else {}

            except (JSONDecodeError, UnicodeDecodeError):
                raise CommandError("Please provide a valid layer settings file")

            layer = Layer.objects.create(name=layer_name,
                                         settings=settings)
            if group_name:
                group, created = LayerGroup.objects.get_or_create(name=group_name)
                group.layers.add(layer)

            if options['verbosity'] > 0:
                self.stdout.write(f"The created layer pk is {layer.pk}, "
                                  "it can be used to import more features"
                                  " in the same layer with different "
                                  "options")

        self.import_datas(layer, file_path, identifier)
        if generate_schema and not layer_pk:
            # only in layer creation, find properties to generate schema
            for key, value in layer.layer_properties.items():
                LayerSchemaProperty.objects.create(slug=key, prop_type='string', layer=layer)
            layer.save()

        if dryrun:
            transaction.savepoint_rollback(sp)
        else:
            transaction.savepoint_commit(sp)

    def import_datas(self, layer, geojson_files, identifier):
        for file_in in geojson_files:
            geojson = file_in.read()
            layer.from_geojson(geojson, identifier)
