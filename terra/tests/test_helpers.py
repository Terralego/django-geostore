import os
from collections import OrderedDict

from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.client import RequestFactory
from rest_framework import status

from terra.helpers import (Choices, ChunkIterator, GeometryDefiner,
                           get_media_response)


class MediaResponseTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_media_response_with_path(self):
        request = self.factory.get('fake/path')

        # Creating a real file
        # In this case, we test if get_media_response return content
        # from a file and so will use open()
        tmp_name = '/tmp/test.txt'
        with open(tmp_name, 'wb') as tmp_file:
            tmp_file.write(b"ceci n'est pas une pipe")

        response = get_media_response(
            request,
            {'path': tmp_name, 'url': None}  # url none, no accel-redirect
        )

        # deleting the file since we don't need it anymore
        os.remove(tmp_name)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.content, bytes)
        self.assertEqual(response.content, b"ceci n'est pas une pipe")

    def test_get_media_response_with_file_object(self):
        request = self.factory.get('fake/path')

        tmp_file = SimpleUploadedFile(name='/tmp/file.txt',
                                      content=b'creativity takes courage')

        # Adding fake url, we don't care, we are not testing accel-redirect
        tmp_file.url = None

        response = get_media_response(request, tmp_file)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.content, bytes)
        self.assertEqual(response.content, b'creativity takes courage')


class ChunkIteratorTest(TestCase):
    def test_chunk_iterator(self):
        chunker = ChunkIterator(iter(range(210)), 20)
        chunks = []

        for chunk in chunker:
            chunks.append(chunk)

        self.assertEqual(11, len(chunks))
        self.assertEqual(10, len(chunks.pop()))

    def test_next_chunk_raise_iterator(self):
        chunker = ChunkIterator(iter(range(0)), 0)
        with self.assertRaises(StopIteration):
            next(chunker)

    def test_next_chunk_iterator(self):
        chunker = ChunkIterator(iter(range(1)), 1)
        self.assertEqual(chunker.next(), [0])


class GeometryDefinerTest(TestCase):
    def test_get_geometry(self):
        geometry_columns = {
            GeometryDefiner.LONGITUDE: 'x',
            GeometryDefiner.LATITUDE: 'y'
        }
        dict_data = OrderedDict([('SIREN', '1'), ('x', '-1.560408'), ('y', '47.218658')])

        geometry = GeometryDefiner.get_geometry(
            column_names=geometry_columns,
            row=dict_data
        )
        self.assertEqual(geometry, Point(-1.560408, 47.218658))

    def test_get_geometry_wrong_data(self):
        geometry_columns = {
            GeometryDefiner.LONGITUDE: 'x',
            GeometryDefiner.LATITUDE: 'y'
        }
        dict_data = OrderedDict([('nothing', '0')])

        geometry = GeometryDefiner.get_geometry(
            column_names=geometry_columns,
            row=dict_data
        )
        self.assertEqual(geometry, None)

        dict_data = OrderedDict([('SIREN', '1'), ('y', '-1.560408')])

        geometry = GeometryDefiner.get_geometry(
            column_names=geometry_columns,
            row=dict_data
        )
        self.assertEqual(geometry, None)

        dict_data = OrderedDict([('SIREN', '1'), ('x', '0')])

        geometry = GeometryDefiner.get_geometry(
            column_names=geometry_columns,
            row=dict_data
        )
        self.assertEqual(geometry, None)

    def test_get_geometry_wrong_type_geometry_columns(self):
        geometry_columns = []
        dict_data = OrderedDict([('nothing', '0')])

        geometry = GeometryDefiner.get_geometry(
            column_names=geometry_columns,
            row=dict_data
        )
        self.assertEqual(geometry, None)

    def test_get_geometry_wrong_order_lat_lng(self):
        geometry_columns = {
            GeometryDefiner.LONGITUDE: 'y',
            GeometryDefiner.LATITUDE: 'x'
        }
        dict_data = OrderedDict([('SIREN', '1'), ('y', '-1.560408'), ('x', '47.218658')])

        geometry = GeometryDefiner.get_geometry(
            column_names=geometry_columns,
            row=dict_data
        )
        self.assertEqual(geometry, Point(-1.560408, 47.218658))


class ChoicesTests(TestCase):
    def setUp(self):
        self.MY_CHOICES = Choices(
            ('ONE', 1, 'One for the money'),
            ('TWO', 2, 'Two for the show'),
            ('THREE', 3, 'Three to get ready'),
        )
        self.MY_CHOICES.add_subset("ODD", ("ONE", "THREE"))

    """
    Testing the choices
    """
    def test_simple_choice(self):
        self.assertEqual(self.MY_CHOICES.CHOICES,
                         ((1, "One for the money"),
                          (2, "Two for the show"),
                          (3, "Three to get ready"),))
        self.assertEqual(self.MY_CHOICES.CHOICES_DICT,
                         {
                             1: 'One for the money',
                             2: 'Two for the show',
                             3: 'Three to get ready'
                         })
        self.assertEqual(self.MY_CHOICES.REVERTED_CHOICES_DICT,
                         {
                             'One for the money': 1,
                             'Three to get ready': 3,
                             'Two for the show': 2
                         })

    def test__contains__(self):
        self.failUnless(self.MY_CHOICES.ONE in self.MY_CHOICES)

    def test__iter__(self):
        self.assertEqual([k for k, v in self.MY_CHOICES], [1, 2, 3])

    def test_unique_values(self):
        self.assertRaises(ValueError, Choices,
                          ('TWO', 4, 'Deux'), ('FOUR', 4, 'Quatre'))

    def test_unique_constants(self):
        self.assertRaises(ValueError, Choices,
                          ('TWO', 2, 'Deux'), ('TWO', 4, 'Quatre'))

    def test_const_choice(self):
        self.assertEqual(self.MY_CHOICES.CONST_CHOICES,
                         (("ONE", "One for the money"),
                          ("TWO", "Two for the show"),
                          ("THREE", "Three to get ready"),))

    def test_value_to_const(self):
        self.assertEqual(self.MY_CHOICES.VALUE_TO_CONST,
                         {1: "ONE", 2: "TWO", 3: "THREE"})

    def test_add_should_add_in_correct_order(self):
        SOME_CHOICES = Choices(
            ('ONE', 1, 'One'),
            ('TWO', 2, 'Two'),
        )
        OTHER_CHOICES = Choices(
            ('THREE', 3, 'Three'),
            ('FOUR', 4, 'Four'),
        )
        # Adding a choices to choices
        tup = SOME_CHOICES + OTHER_CHOICES
        self.assertEqual(tup, ((1, 'One'), (2, 'Two'),
                               (3, 'Three'), (4, 'Four')))

        # Adding a tuple to choices
        tup = SOME_CHOICES + ((3, 'Three'), (4, 'Four'))
        self.assertEqual(tup, ((1, 'One'), (2, 'Two'),
                               (3, 'Three'), (4, 'Four')))

        """Adding a choices to tuple => do not work; is it possible to
           emulate it?
            tup = ((1, 'One'), (2, 'Two')) + OTHER_CHOICES
            self.assertEqual(tup, ((1, 'One'), (2, 'Two'),
                                   (3, 'Three'), (4, 'Four')))
        """

    def test_retrocompatibility(self):
        MY_CHOICES = Choices(
            ('TWO', 2, 'Deux'),
            ('FOUR', 4, 'Quatre'),
            name="EVEN"
        )
        MY_CHOICES.add_choices("ODD",
                               ('ONE', 1, 'Un'),
                               ('THREE', 3, 'Trois'),)
        self.assertEqual(MY_CHOICES.CHOICES, ((2, 'Deux'), (4, 'Quatre'),
                                              (1, 'Un'), (3, 'Trois')))
        self.assertEqual(MY_CHOICES.ODD, ((1, 'Un'), (3, 'Trois')))
        self.assertEqual(MY_CHOICES.EVEN, ((2, 'Deux'), (4, 'Quatre')))


class SubsetTests(TestCase):
    def setUp(self):
        self.MY_CHOICES = Choices(
            ('ONE', 1, 'One for the money'),
            ('TWO', 2, 'Two for the show'),
            ('THREE', 3, 'Three to get ready'),
        )
        self.MY_CHOICES.add_subset("ODD", ("ONE", "THREE"))
        self.MY_CHOICES.add_subset("ODD_BIS", ("ONE", "THREE"))

    def test_basic(self):
        self.assertEqual(self.MY_CHOICES.ODD, ((1, 'One for the money'),
                                               (3, 'Three to get ready')))

    def test__contains__(self):
        self.failUnless(self.MY_CHOICES.ONE in self.MY_CHOICES.ODD)

    def test__eq__(self):
        self.assertEqual(self.MY_CHOICES.ODD, ((1, 'One for the money'),
                                               (3, 'Three to get ready')))
        self.assertEqual(self.MY_CHOICES.ODD, self.MY_CHOICES.ODD_BIS)
