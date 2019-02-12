import subprocess
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from terracommon.terra.models import Feature
from terracommon.terra.tests.factories import LayerFactory
from terracommon.terra.tests.utils import get_files_tests


class ImportGeojsonTest(TestCase):

    def get_good_data(self):
        overpass_path = get_files_tests('overpass.osm')
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
        output = StringIO()
        call_command(
            'import_osm',
            f'{query}',
            f'-t{type_feature}',
            '-v 1', stderr=output)
        self.assertIn("Warning 1", output.getvalue())
        self.assertEqual(Feature.objects.count(), 2)

    @mock.patch('requests.get')
    def test_good_query_on_existing_layer(self, mocked_get):
        layer = LayerFactory()
        type_feature = 'points'
        mocked_get.return_value.status_code = 200
        mocked_get.return_value.content = self.get_good_data()
        query = 'good query'
        output = StringIO()
        call_command(
            'import_osm',
            f'{query}',
            f'-pk={layer.pk}',
            f'-t{type_feature}',
            '-v 1', stderr=output)
        self.assertIn("Warning 1", output.getvalue())
        self.assertEqual(layer.features.count(), 2)

    @mock.patch('requests.get')
    @mock.patch('terracommon.terra.management.commands.import_osm.Command.launch_cmd_ogr2ogr')
    def test_ogr2ogr_fail(self, mock_ogr2ogr_stdout, mocked_get):
        def command_ogr2ogr_fail(content, type_features):
            return '', 'Error'
        mock_ogr2ogr_stdout.side_effect = command_ogr2ogr_fail
        type_feature = 'points'
        mocked_get.return_value.status_code = 200
        mocked_get.return_value.content = self.get_good_data()
        query = 'good query'
        with self.assertRaises(CommandError) as error:
            call_command(
                'import_osm',
                f'{query}',
                f'-t{type_feature}',
                '-v 0')
        self.assertEqual("Ogr2ogr failed to create the geojson", str(error.exception))

    @mock.patch('requests.get')
    @mock.patch('subprocess.run')
    def test_ogr2ogr_fail_calledprocess(self, mock_ogr2ogr_raise, mocked_get):
        def command_ogr2ogr_fail(args, stdout, stderr, encoding):
            raise subprocess.CalledProcessError(1, 2)
        mock_ogr2ogr_raise.side_effect = command_ogr2ogr_fail
        type_feature = 'points'
        mocked_get.return_value.status_code = 200
        mocked_get.return_value.content = self.get_good_data()
        query = 'good query'
        with self.assertRaises(CommandError) as error:
            call_command(
                'import_osm',
                f'{query}',
                f'-t{type_feature}',
                '-v 0')
        self.assertEqual("Command ogr2ogr failed", str(error.exception))
