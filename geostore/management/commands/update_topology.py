from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

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

        parser.add_argument('--dry-run',
                            action="store_true",
                            help='Execute une dry-run mode')

    @transaction.atomic()
    def handle(self, *args, **options):
        layer_pk = options.get('layer_pk', None)
        dryrun = options.get('dry_run', None)

        sp = transaction.savepoint()
        try:
            layer = Layer.objects.get(pk=layer_pk)
        except Layer.DoesNotExist:
            raise CommandError(f"Layer with pk {layer_pk} doesn't exist")
        if Routing.create_topology(layer):
            if options['verbosity'] >= 1:
                self.stdout.write('Topology successfully updated')
        else:
            raise CommandError('An error occuring during topology update')

        if dryrun:
            transaction.savepoint_rollback(sp)
        else:
            transaction.savepoint_commit(sp)
