from django.core.management.base import BaseCommand
from django.db import transaction

from terracommon.terra.models import Layer
from terracommon.terra.routing.helpers import Routing


class Command(BaseCommand):
    help = 'Update pgRouting topology'

    def add_arguments(self, parser):
        parser.add_argument('-pk',
                            '--layer-pk',
                            type=int,
                            action="store",
                            help=("PK of the layer where to insert"
                                  "the features.\n"
                                  "A new layer is created if not "
                                  "present."))

        parser.add_argument('--dry-run',
                            action="store_true",
                            help='Execute une dry-run mode')

    @transaction.atomic()
    def handle(self, *args, **options):
        layer_pk = options.get('layer_pk', None)
        dryrun = options.get('dry_run', None)

        sp = transaction.savepoint()

        layer = Layer.objects.get(pk=layer_pk)

        if Routing.create_topology(layer):
            self.stdout.write('Topology successfully updated')
        else:
            self.stdout.write('An error occuring during topology update')

        if dryrun:
            transaction.savepoint_rollback(sp)
        else:
            transaction.savepoint_commit(sp)
