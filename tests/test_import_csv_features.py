import csv
import tempfile

from django.contrib.gis.geos import Point
from django.test import TestCase

from terracommon.terra.models import Layer


class ImportCSVFeaturesTestCase(TestCase):
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

    def test_simple_import(self):
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
        self.layer.from_csv_dictreader(reader, ['CODGEO'])

        expected = initial + 1
        self.assertEqual(self.layer.features.all().count(), expected)

    def test_init_options(self):

        """Create fake features to test features reinit"""
        for i in range(2):
            self.layer.features.create(geom=Point(),
                                       properties={'SIREN': '', 'NIC': ''}, )
        self.assertEqual(self.layer.features.all().count(), 2)

        reader = self.get_csv_reader_from_dict(
            ['SIREN', 'NIC', 'L1_NORMALISEE', 'L2_NORMALISEE',
             'L3_NORMALISEE'],
            [['518521414', '00038', '11 RUE DU MARCHIX', '44000 NANTES',
              'France'],
             ['518521414', '00053', '52 RUE JACQUES BABINET', '31100 TOULOUSE',
              'France'],
             ['813792686', '00012', 'BOIS DE TULLE', '32700 LECTOURE',
              'France'],
             ['822869632', '00023', '52 RUE JACQUES BABINET', '31100 TOULOUSE',
              'France']]
        )

        self.layer.from_csv_dictreader(reader, ['SIREN', 'NIC'], init=True)

        """Init mode only create new items, it does not reset database"""
        self.assertEqual(self.layer.features.all().count(), 6)

        feature = self.layer.features.get(properties__SIREN='813792686',
                                          properties__NIC='00012')
        self.assertEqual(feature.properties.get('L1_NORMALISEE', ''),
                         'BOIS DE TULLE')

    def test_create_update(self):
        self.layer.features.create(
            geom=Point(),
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
             'L3_NORMALISEE'],
            [['437582422', '00097', '52 RUE JACQUES BABINET', '31100 TOULOUSE',
              'France'],
             ['518521414', '00038', '11 RUE DU MARCHIX', '44000 NANTES',
              'France']]
        )

        self.layer.from_csv_dictreader(reader, ['SIREN', 'NIC'])

        expected = initial + 1
        self.assertEqual(self.layer.features.all().count(), expected)

        feature = self.layer.features.get(properties__SIREN='437582422',
                                          properties__NIC='00097')
        self.assertEqual(feature.properties.get('L1_NORMALISEE', ''),
                         '52 RUE JACQUES BABINET')
