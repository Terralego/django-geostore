import csv
import json
import tempfile

from django.contrib.gis.geos import GEOSException, GEOSGeometry, Point
from django.test import TestCase
from rest_framework.test import APIClient

from terracommon.terra.models import Layer
from terracommon.terra.tests.factories import (FeatureFactory, LayerFactory,
                                               UserFactory)
from terracommon.terra.tests.utils import get_files_tests
from terracommon.terra.transformations import set_geometry_from_options


class LayerFromCSVDictReaderTestCase(TestCase):
    def setUp(self):
        self.layer = Layer.objects.create(name='fake layer')

    def get_csv_reader_from_dict(self, fieldnames, rows):
        self.tmp_file = tempfile.NamedTemporaryFile(mode='r+',
                                                    encoding='iso-8859-15',
                                                    delete=False)

        writer = csv.writer(self.tmp_file.file, )
        writer.writerow(fieldnames)
        writer.writerows(rows)
        self.tmp_file.file.seek(0)

        return csv.DictReader(self.tmp_file.file, )

    def test_missing_coordinates(self):
        reader = self.get_csv_reader_from_dict(
            ['CODGEO', 'Nb Pharmacies et parfumerie',
             'Dynamique Entrepreneuriale', 'Nb Résidences Principales',
             'Nb propriétaire', 'Nb Logement', 'Nb Résidences Secondaires',
             'Nb Log Vacants', 'Nb Occupants Résidence Principale',
             'Nb Femme', 'Nb Homme', 'Nb Mineurs', 'Nb Majeurs',
             'Nb Etudiants', 'CP'],
            [[1006, 0, 42, 41, 28, 57, 13, 3, 86, 86, 86, 101, 71, 2, 1], ]
        )

        initial = self.layer.features.all().count()
        self.layer.from_csv_dictreader(reader=reader,
                                       options=[],
                                       operations=[],
                                       pk_properties=['CODGEO'])

        expected = initial
        self.assertEqual(self.layer.features.all().count(), expected)

    def test_init_options(self):
        """Create fake features to test features reinit"""
        for i in range(2):
            self.layer.features.create(geom=Point(),
                                       properties={'SIREN': '', 'NIC': ''}, )
        self.assertEqual(self.layer.features.all().count(), 2)

        reader = self.get_csv_reader_from_dict(
            ['SIREN', 'NIC', 'L1_NORMALISEE', 'L2_NORMALISEE',
             'L3_NORMALISEE', 'x', 'y'],
            [['518521414', '00038', '11 RUE DU MARCHIX', '44000 NANTES',
              'France', '-1.560408', '47.218658'],
             ['518521414', '00053', '52 RUE JACQUES BABINET', '31100 TOULOUSE',
              'France', '1.408246', '43.575224'],
             ['813792686', '00012', 'BOIS DE TULLE', '32700 LECTOURE',
              'France', '1.538103', '45.17995'],
             ['822869632', '00023', '52 RUE JACQUES BABINET', '31100 TOULOUSE',
              'France', '1.408246', '43.575224']]
        )

        options = {
            'longitude': 'x',
            'latitude': 'y',
        }
        operations = [
            set_geometry_from_options,
        ]

        self.layer.from_csv_dictreader(reader=reader,
                                       options=options,
                                       operations=operations,
                                       pk_properties=['SIREN', 'NIC'],
                                       init=True)

        # Init mode only create new items, it does not reset database
        self.assertEqual(self.layer.features.all().count(), 6)

        feature = self.layer.features.get(properties__SIREN='813792686',
                                          properties__NIC='00012')
        self.assertEqual(feature.properties.get('L1_NORMALISEE', ''),
                         'BOIS DE TULLE')

    def test_create_update(self):
        self.layer.features.create(
            geom=Point(1.405812, 43.574511),
            properties={
                'SIREN': '437582422',
                'NIC': '00097',
                'L1_NORMALISEE': '36 RUE JACQUES BABINET',
                'L2_NORMALISEE': '31100 TOULOUSE',
                'L3_NORMALISEE': 'France',
            },
        )
        initial = self.layer.features.all().count()

        reader = self.get_csv_reader_from_dict(
            ['SIREN', 'NIC', 'L1_NORMALISEE', 'L2_NORMALISEE',
             'L3_NORMALISEE', 'long', 'lat'],
            [['437582422', '00097', '52 RUE JACQUES BABINET', '31100 TOULOUSE',
              'France', '1.408246', '43.575224'],
             ['518521414', '00038', '11 RUE DU MARCHIX', '44000 NANTES',
              'France', '-1.560408', '47.218658']]
        )

        options = {
            'longitude': 'long',
            'latitude': 'lat',
        }
        operations = [
            set_geometry_from_options,
        ]

        self.layer.from_csv_dictreader(reader=reader,
                                       options=options,
                                       operations=operations,
                                       pk_properties=['SIREN', 'NIC'])

        expected = initial + 1
        self.assertEqual(self.layer.features.all().count(), expected)

        feature = self.layer.features.get(properties__SIREN='437582422',
                                          properties__NIC='00097')
        self.assertEqual(feature.properties.get('L1_NORMALISEE', ''),
                         '52 RUE JACQUES BABINET')

    def test_operations(self):
        self.layer.features.create(
            geom=Point(1.405812, 43.574511),
            properties={
                'SIREN': '437582422',
                'NIC': '00097',
                'L1_NORMALISEE': '36 RUE JACQUES BABINET',
                'L2_NORMALISEE': '31100 TOULOUSE',
                'L3_NORMALISEE': 'France',
            },
        )

        reader = self.get_csv_reader_from_dict(
            ['SIREN', 'NIC', 'L1_NORMALISEE', 'L2_NORMALISEE',
             'L3_NORMALISEE', 'x', 'y'],
            [['437582422', '00097', '52 RUE JACQUES BABINET', '31100 TOULOUSE',
              'France', '1.408246', '43.575224']]
        )

        def custom_transformation(feature_args, options):
            properties = feature_args.get('properties')
            if properties.get('x'):
                properties['long'] = properties['x']
                del properties['x']
            if properties.get('y'):
                properties['lat'] = properties['y']
                del properties['y']
            feature_args['properties'] = properties

        options = {
            'latitude': 'lat',
            'longitude': 'long',
        }
        operations = [
            custom_transformation,
            set_geometry_from_options,
        ]
        self.layer.from_csv_dictreader(reader=reader,
                                       options=options,
                                       operations=operations,
                                       pk_properties=['SIREN', 'NIC'])

        feature = self.layer.features.get(properties__SIREN='437582422',
                                          properties__NIC='00097')
        self.assertEqual((1.408246, 43.575224), feature.geom.coords)


class LayerFromGeojsonTestCase(TestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.user = UserFactory()
        self.client.force_login(self.user)

    def test_import_geojson_with_projection(self):
        with_projection = """{"type": "FeatureCollection", "crs":
                             { "type": "name", "properties": { "name":
                             "urn:ogc:def:crs:OGC:1.3:CRS84" } },
                             "features": []}"""
        self.layer.from_geojson(with_projection, "01-01", "01-01")

    def test_import_geojson_withtout_projection(self):
        without_projection = """{"type": "FeatureCollection",
                                "features": []}"""
        self.layer.from_geojson(without_projection, "01-01", "01-01")

        with_bad_projection = """{"type": "FeatureCollection", "crs":
                                 { "type": "name", "properties": { "name":
                                 "BADPROJECTION" } }, "features": []}"""
        with self.assertRaises(GEOSException):
            self.layer.from_geojson(with_bad_projection, "01-01", "01-01")


class LayerFromShapefileTestCase(TestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.user = UserFactory()
        self.client.force_login(self.user)

    def test_shapefile_import(self):
        layer = LayerFactory()
        shapefile_path = get_files_tests('shapefile-WGS84.zip')

        with open(shapefile_path, 'rb') as shapefile:
            layer.from_shapefile(shapefile)

        self.assertEqual(8, layer.features.all().count())


class LayerExportGeometryTestCase(TestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.fake_geometry = {
            "type": "Point",
            "coordinates": [
                2.,
                45.
            ]
        }

    def test_to_geojson(self):
        # Create at least one feature in the layer, so it's not empty
        FeatureFactory(layer=self.layer)
        FeatureFactory(
            layer=self.layer,
            geom=GEOSGeometry(json.dumps(self.fake_geometry)),
            properties={'number': 1, 'digit': 34},
        )
        self.assertEqual(str(self.layer.to_geojson()['features'][0]['geometry']),
                         "{'type': 'Point', 'coordinates': [2.4609375, 45.583289756006316]}")
        self.assertEqual(str(self.layer.to_geojson()['features'][1]['geometry']),
                         "{'type': 'Point', 'coordinates': [2.0, 45.0]}")
        self.assertEqual(str(self.layer.to_geojson()['features'][1]['properties']),
                         "{'digit': 34, 'number': 1}")


class LayerSettingsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.layer = LayerFactory()
        self.user = UserFactory()
        self.client.force_authenticate(self.user)

    def test_layer_settings(self):
        with self.assertRaises(KeyError):
            self.layer.layer_settings('foo', 'bar', '666')

        with self.assertRaises(KeyError):
            self.layer.layer_settings('tiles', 'minzoom')

        self.assertEqual(
            self.layer.layer_settings_with_default('tiles', 'minzoom'),
            0
        )

    def test_set_layer_settings(self):
        with self.assertRaises(KeyError):
            self.layer.layer_settings('foo', 'bar')

        self.layer.set_layer_settings('foo', 'bar', 123)

        self.assertEqual(
            self.layer.layer_settings('foo', 'bar'),
            123
        )

        self.assertEqual(
            self.layer.layer_settings_with_default('foo', 'bar'),
            123
        )
