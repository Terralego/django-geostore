import logging

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from geostore.transformations import set_geometry_from_options
from geostore.models import Layer
from geostore.tests.utils import get_files_tests

UserModel = get_user_model()


class ImportCSVTestCase(TestCase):
    def test_command_launch(self):
        test_file = get_files_tests('test.csv')
        with self.assertLogs(level=logging.WARNING) as cm:
            call_command('import_csv',
                         ('--operation=geostore.transformations'
                          '.set_geometry_from_options'),
                         '--layer=companies',
                         '--key=SIREN',
                         '--key=NIC',
                         '--bulk',
                         f'--source={test_file}')
        self.assertEqual(len(cm.records), 1)
        log_record = cm.records[0]
        self.assertEqual(set_geometry_from_options.__name__,
                         log_record.funcName)
        self.assertIn('019778745', log_record.msg)  # SIREN key
        self.assertIn('00018', log_record.msg)  # NIC key
        self.assertIsNotNone(Layer.objects.filter(name="companies"))
