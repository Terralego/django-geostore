import logging

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Populate database from all installed app's initialization modules"

    POPULATE_MODULE_NAME = 'populate'
    POPULATE_FN_NAME = 'load_data'
    POPULATE_TEST_FN_NAME = 'load_test_data'

    def add_arguments(self, parser):
        parser.add_argument('-d', '--dry-run',
                            action="store_true",
                            help='Dry-run mode')
        parser.add_argument('-t', '--test-data',
                            action="store_true",
                            help='Load test data')
        parser.add_argument('-l', '--list',
                            action="store_true",
                            help='List available modules')
        parser.add_argument('-m', '--modules',
                            action="store",
                            nargs="?",
                            help="Load data for this modules")

    def handle(self, *args, **options):
        self.test_mode = True if options.get('test_data') else False

        if options.get('list', False):
            self.stdout.write('Applications with populate modules:')
            for app_name in self.available_modules.keys():
                self.stdout.write('  - {}'.format(app_name))
            exit(0)

        sid = transaction.savepoint()

        for app_name, load_data_fn in self.available_modules.items():
            with transaction.atomic():
                self.stdout.write('Loading data for {}'.format(app_name))
                load_data_fn()

        if options.get('dry_run'):
            transaction.savepoint_rollback(sid)

    @cached_property
    def available_modules(self):
        available_modules = {}

        fn_name = self.POPULATE_TEST_FN_NAME \
            if self.test_mode else self.POPULATE_FN_NAME

        for app_name, app_config in apps.app_configs.items():
            try:
                available_modules[app_name] = import_string("{}.{}.{}".format(
                    app_config.module.__package__,
                    self.POPULATE_MODULE_NAME,
                    fn_name))
            except ImportError:
                logger.debug('Application {} has no'
                             ' populate module'.format(app_name))

        return available_modules
