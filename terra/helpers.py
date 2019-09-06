import io
import logging
import os
import zipfile

from django.contrib.gis.geos.point import Point

logger = logging.getLogger(__name__)


def make_zipfile_bytesio(base_dir):
    zip_file = io.BytesIO()

    with zipfile.ZipFile(zip_file, "w",
                         compression=zipfile.ZIP_DEFLATED) as zf:
        path = os.path.normpath(base_dir)
        if path != os.curdir and path != base_dir:
            zf.write(path, os.path.relpath(path, base_dir))
            logger.info("adding '%s'", path)
        for dirpath, dirnames, filenames in os.walk(base_dir):
            for name in sorted(dirnames):
                path = os.path.normpath(os.path.join(dirpath, name))
                zf.write(path, os.path.relpath(path, base_dir))
                logger.info("adding '%s'", path)
            for name in filenames:
                path = os.path.normpath(os.path.join(dirpath, name))
                if os.path.isfile(path):
                    zf.write(path, os.path.relpath(path, base_dir))
                    logger.info("adding '%s'", path)

    return zip_file


class ChunkIterator:

    def __init__(self, iterator, chunksize):
        self.iterator = iterator
        self.chunksize = chunksize

    def __iter__(self):
        return self

    def __next__(self):
        try:
            chunk = []
            for i in range(self.chunksize):
                chunk.append(next(self.iterator))
        finally:
            if chunk:
                return chunk
            else:
                raise StopIteration

    def next(self):
        return self.__next__()


class GeometryDefiner:
    LONGITUDE = 'longitude'
    LATITUDE = 'latitude'

    @staticmethod
    def get_geometry(column_names, row):
        if not isinstance(column_names, dict):
            return None
        if sorted(column_names.keys()) == [GeometryDefiner.LATITUDE,
                                           GeometryDefiner.LONGITUDE]:
            lat_column = column_names.get(GeometryDefiner.LATITUDE)
            long_column = column_names.get(GeometryDefiner.LONGITUDE)
            if all(row.get(column) for column in [long_column, lat_column]):
                x = float(row.get(long_column))
                y = float(row.get(lat_column))
                return Point(x, y)
        return None
