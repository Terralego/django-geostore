import argparse
import csv
import sys

from django.core.management import BaseCommand
from django.utils.module_loading import import_string
from django.utils.translation import ugettext as _

from geostore.models import Layer


class Command(BaseCommand):
    help = _('Import insee data from csv to db.')

    def add_arguments(self, parser):
        parser.add_argument('-b', '--bulk',
                            action='store_true',
                            dest='bulk',
                            default=False,
                            help=_("Delete all stored INSEE data,"
                                   " DO NOT USE IN PROD.")
                            )
        parser.add_argument('-c', '--creations-per-transaction',
                            dest='chunk_size',
                            type=int,
                            default=1000,
                            help=_('Number of rows per transaction')
                            )
        parser.add_argument('-cd', '--delimiter',
                            action='store',
                            dest='delimiter',
                            default=';',
                            required=False,
                            help=_('Specify CSV delimiter')
                            )
        parser.add_argument('-cq', '--quotechar',
                            action='store',
                            dest='quotechar',
                            default='"',
                            required=False,
                            help=_('Specify CSV quotechar')
                            )
        parser.add_argument('-cs', '--source',
                            dest='source',
                            type=argparse.FileType('r',
                                                   encoding='iso-8859-15'),
                            default=sys.stdin,
                            required=True,
                            help=_('Specify CSV path'),
                            )
        parser.add_argument('-f', '--fast',
                            action='store_true',
                            default=False,
                            help=_("If present and it's not an initial import"
                                   " will speed up features creation. But no"
                                   " rollback is possible. If something broke"
                                   " up during import, the import will stop "
                                   " with half data in database.")
                            )
        parser.add_argument('-i', '--init',
                            action='store_true',
                            dest='init',
                            default=False,
                            help=_('Improve performance of initial import')
                            )
        parser.add_argument('-k', '--key',
                            required=True,
                            action='append',
                            dest='pk_properties',
                            help=_("Define primary keys of this data."
                                   " Example with companies:"
                                   " --key=SIREN --key=NIC"
                                   " Example with INSEE:"
                                   " --key=code_insee")
                            )
        parser.add_argument('-l', '--layer',
                            required=True,
                            action='store',
                            dest='layer',
                            help=_('Specify layer name')
                            )
        parser.add_argument('-o', '--operation',
                            required=True,
                            action='append',
                            dest='operations',
                            help=_('Specify transform functions')
                            )
        parser.add_argument('--longitude',
                            required=False,
                            action='store',
                            dest='longitude',
                            help=_('Name of longitude column')
                            )
        parser.add_argument('--latitude',
                            required=False,
                            action='store',
                            dest='latitude',
                            help=_('Name of latitude column')
                            )

    def handle(self, *args, **options):
        layer_name = options.get('layer')
        layer = Layer.objects.get_or_create(name=layer_name)[0]

        if options['bulk']:
            layer.features.all().delete()

        operations = None
        if options['operations']:
            operations = [import_string(path) for path in
                          options.get('operations')]

        reader = csv.DictReader(options.get('source'),
                                delimiter=options.get('delimiter'),
                                quotechar=options.get('quotechar'))

        layer.from_csv_dictreader(
            reader=reader,
            options=options,
            operations=operations,
            pk_properties=options.get('pk_properties'),
            init=options.get('init'),
            chunk_size=options.get('chunk_size'),
            fast=options.get('fast')
        )
