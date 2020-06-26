from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import gettext as _

from geostore.models import Layer
from geostore.routing.helpers import Routing


class Command(BaseCommand):
    help = 'Update pgRouting topology'

    def add_arguments(self, parser):
        parser.add_argument('-pk',
                            '--layer-pk',
                            type=int,
                            action="store",
                            required=True,
                            help=("PK of the layer where to insert"
                                  "the features.\n"
                                  ))
        parser.add_argument('-t',
                            '--tolerance',
                            type=float,
                            action="store",
                            required=False,
                            help=_("Tolerance for snapping topologies (default to 0.00001)."))

    @transaction.atomic()
    def handle(self, *args, **options):
        layer_pk = options.get('layer_pk', None)
        tolerance = options.get('tolerance', 0.00001)

        try:
            layer = Layer.objects.get(pk=layer_pk)
            if Routing.create_topology(layer, tolerance=tolerance):
                if options['verbosity'] >= 1:
                    self.stdout.write('Topology successfully updated')

            else:
                raise CommandError('An error occuring during topology update')

        except Layer.DoesNotExist:
            raise CommandError(f"Layer with pk {layer_pk} doesn't exist")
