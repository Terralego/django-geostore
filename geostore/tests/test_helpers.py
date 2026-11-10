import os
import tempfile
import zipfile
from collections import OrderedDict

from django.contrib.gis.geos import Point
from django.test import TestCase

from geostore.import_export.helpers import (
    ChunkIterator,
    GeometryDefiner,
    make_zipfile_bytesio,
)


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
            GeometryDefiner.LONGITUDE: "x",
            GeometryDefiner.LATITUDE: "y",
        }
        dict_data = OrderedDict(
            [("SIREN", "1"), ("x", "-1.560408"), ("y", "47.218658")]
        )

        geometry = GeometryDefiner.get_geometry(
            column_names=geometry_columns, row=dict_data
        )
        self.assertEqual(geometry, Point(-1.560408, 47.218658))

    def test_get_geometry_wrong_data(self):
        geometry_columns = {
            GeometryDefiner.LONGITUDE: "x",
            GeometryDefiner.LATITUDE: "y",
        }
        dict_data = OrderedDict([("nothing", "0")])

        geometry = GeometryDefiner.get_geometry(
            column_names=geometry_columns, row=dict_data
        )
        self.assertEqual(geometry, None)

        dict_data = OrderedDict([("SIREN", "1"), ("y", "-1.560408")])

        geometry = GeometryDefiner.get_geometry(
            column_names=geometry_columns, row=dict_data
        )
        self.assertEqual(geometry, None)

        dict_data = OrderedDict([("SIREN", "1"), ("x", "0")])

        geometry = GeometryDefiner.get_geometry(
            column_names=geometry_columns, row=dict_data
        )
        self.assertEqual(geometry, None)

    def test_get_geometry_wrong_type_geometry_columns(self):
        geometry_columns = []
        dict_data = OrderedDict([("nothing", "0")])

        geometry = GeometryDefiner.get_geometry(
            column_names=geometry_columns, row=dict_data
        )
        self.assertEqual(geometry, None)

    def test_get_geometry_wrong_order_lat_lng(self):
        geometry_columns = {
            GeometryDefiner.LONGITUDE: "y",
            GeometryDefiner.LATITUDE: "x",
        }
        dict_data = OrderedDict(
            [("SIREN", "1"), ("y", "-1.560408"), ("x", "47.218658")]
        )

        geometry = GeometryDefiner.get_geometry(
            column_names=geometry_columns, row=dict_data
        )
        self.assertEqual(geometry, Point(-1.560408, 47.218658))


class MakeZipfileBytesIOTest(TestCase):
    def test_make_zipfile_with_subdirs_and_trailing_slash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "subfolder")
            os.makedirs(subdir)
            file_path = os.path.join(subdir, "hello.txt")
            with open(file_path, "w") as f:
                f.write("world")

            base_dir_with_slash = tmpdir + os.sep
            bio = make_zipfile_bytesio(base_dir_with_slash)
            with zipfile.ZipFile(bio, "r") as zf:
                namelist = zf.namelist()
                self.assertIn("subfolder/hello.txt", namelist)
