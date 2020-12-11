import io
import json
import logging
import os
import zipfile

from django.contrib.gis.geos import Point
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.template.loader import get_template
from django.utils.timezone import now
from django.utils.translation import gettext as _

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


def send_mail_export(user, path=None):
    url = default_storage.url(path)
    context = {"username": user.get_username(), "url": url}
    if not path:
        template_email = 'exports_no_data'
    else:
        template_email = 'exports'
    html = get_template('geostore/emails/{}.html'.format(template_email))
    html_content = html.render(context)
    txt = get_template('geostore/emails/{}.txt'.format(template_email))
    txt_content = txt.render(context)
    send_mail(_('Your data export is ready'), txt_content, None, [getattr(user, user.get_email_field_name())],
              html_message=html_content, fail_silently=True)


def save_generated_file(user_id, layer_name, format_file, string_file):
    string_file = string_file.encode('utf-8') if not isinstance(string_file, bytes) else string_file
    path = default_storage.save('exports/users/{}/{}_{}.{}'.format(user_id,
                                                                   layer_name,
                                                                   int(now().timestamp()),
                                                                   format_file),
                                ContentFile(string_file))
    return path


class ChunkIterator:
    def __init__(self, iterator, chunksize):
        self.iterator = iterator
        self.chunksize = chunksize

    def __iter__(self):
        return self

    def __next__(self):
        chunk = []
        try:
            for i in range(self.chunksize):
                chunk.append(next(self.iterator))
        finally:
            if chunk:
                return chunk
            else:
                raise StopIteration

    def next(self):
        return self.__next__()


def get_serialized_properties(layer, feature_properties):
    properties = {k: None for k in layer.layer_properties}
    for prop, value in feature_properties.items():
        if isinstance(value, str):
            properties[prop] = value
        else:
            properties[prop] = json.dumps(value)
    return properties


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
