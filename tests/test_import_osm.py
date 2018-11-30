import os
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from terracommon.terra.models import Feature


class ImportGeojsonTest(TestCase):

    def get_good_data(self):
        overpass_path = os.path.join(os.path.dirname(__file__),
                                     'files',
                                     'overpass.osm')
        with open(overpass_path, 'rb') as overpass_file:
            overpass_data = overpass_file.read()
        return overpass_data

    @mock.patch('requests.get')
    def test_bad_query(self, mocked_get):
        type_feature = 'points'
        mocked_get.return_value.status_code = 400
        mocked_get.return_value.content = b"test"

        query = "bad query"
        self.assertRaises(CommandError, call_command,
                          'import_osm', f'{query}', f'-t{type_feature}')

    @mock.patch('requests.get')
    def test_overpass_down(self, mocked_get):
        type_feature = 'points'
        mocked_get.return_value.status_code = 404
        mocked_get.return_value.content = b""

        query = "good query"
        self.assertRaises(CommandError, call_command,
                          'import_osm', f'{query}', f'-t{type_feature}')

    @mock.patch('requests.get')
    def test_good_query(self, mocked_get):
        type_feature = 'points'
        mocked_get.return_value.status_code = 200
        mocked_get.return_value.content = self.get_good_data()
        query = 'good query'
        call_command(
            'import_osm',
            f'{query}',
            f'-t{type_feature}',
            '-v 0')
        self.assertEqual(Feature.objects.count(), 2)
