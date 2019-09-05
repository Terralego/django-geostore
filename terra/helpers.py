import io
import logging
import os
import zipfile

import magic
from django.conf import settings
from django.contrib.gis.geos.point import Point
from django.core.files import File
from django.http import HttpResponse, HttpResponseForbidden

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


def get_media_response(request, data, permissions=None, headers=None):
    # For compatibility purpose
    content, url = None, None
    if isinstance(data, (io.IOBase, File)):
        content, url = data, data.url
    else:
        # https://docs.djangoproject.com/fr/2.1/ref/request-response/#passing-iterators # noqa
        content, url = open(data['path'], mode='rb'), data['url']

    filetype = magic.from_buffer(content.read(1024), mime=True)
    content.seek(0)

    if isinstance(permissions, list):
        if not set(permissions).intersection(
                request.user.get_all_permissions()):
            return HttpResponseForbidden()

    response = HttpResponse(content_type='application/octet-stream')
    if isinstance(headers, dict):
        for header, value in headers.items():
            response[header] = value

    if settings.MEDIA_ACCEL_REDIRECT:
        response['X-Accel-Redirect'] = f'{url}'
    else:
        response.content = content.read()
        response.content_type = filetype

    return response


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


class Choices:
    """
    Class under GPL Licence from:
    https://github.com/liberation/django-extended-choices/
    Helper class for choices fields in Django.
    A choice value has three representation (constant name, value and
    string). So Choices takes list of such tuples.
    Here is an example of Choices use:
    >>> CHOICES_ALIGNEMENT = Choices(
    ...     ('BAD', 10, u'bad'),
    ...     ('NEUTRAL', 20, u'neutral'),
    ...     ('CHAOTIC_GOOD', 30, u'chaotic good'),
    ...     ('GOOD', 40, u'good'),
    ... )
    >>> CHOICES_ALIGNEMENT.BAD
    10
    >>> CHOICES_ALIGNEMENT.CHOICES_DICT[30]
    u'chaotic good'
    >>> CHOICES_ALIGNEMENT.REVERTED_CHOICES_DICT[u'good']
    40
    As you can see in the above example usage, Choices objects gets three
    attributes:
    - one attribute built after constant names provided in the tuple (like BAD,
      NEUTRAL etc...)
    - a CHOICES_DICT that match value to string
    - a REVERTED_CHOICES_DICT that match string to value
    If you want to create subset of choices, you can
    use the add_subset method
    This method take a name, and then the constants you want to
    have in this subset:
    >>> CHOICES_ALIGNEMENT.add_subset('WESTERN',('BAD', 'GOOD'))
    >>> CHOICES_ALIGNEMENT.WESTERN
    ((10, u'bad'), (40, u'good'))
    """

    def __init__(self, *raw_choices, **kwargs):
        self._CHOICES = None
        self._CHOICES_DICT = None
        self._REVERTED_CHOICES_DICT = None
        self._VALUE_TO_CONST = None
        self._RAW_CHOICES = None
        self._CONSTS = []
        self._CONST_CHOICES = None
        self.parent = None
        if "parent" in kwargs:  # 'subchoice' mode
            self.parent = kwargs["parent"]
            self._CONSTS = kwargs["CONSTS"]
        else:
            name = kwargs.get('name', 'CHOICES')  # retrocompatibility
            if name != "CHOICES":  # retrocompatibility
                self._RAW_CHOICES = tuple()
                self.add_choices(name, *raw_choices)
            else:
                self._RAW_CHOICES = raw_choices  # default behaviour
                self._make_consts(*raw_choices)

    def _make_consts(self, *raw_choices):
        for choice in raw_choices:
            const, value, string = choice
            if hasattr(self, const):
                raise ValueError("You cannot declare two constants "
                                 "with the same name! %s " % str(choice))
            if value in [getattr(self, c) for c in self._CONSTS]:
                raise ValueError("You cannot declare two constants "
                                 "with the same value! %s " % str(choice))
            setattr(self, const, value)
            self._CONSTS.append(const)

            # retrocompatibilty
            self._CHOICES = None
            self._CHOICES_DICT = None
            self._REVERTED_CHOICES_DICT = None

    def add_choices(self, name="CHOICES", *raw_choices):
        # for retrocompatibility
        # we may have to call _build_choices
        # more than one time and so append the
        # new choices to the already existing ones
        RAW_CHOICES = list(self._RAW_CHOICES)
        self._RAW_CHOICES = tuple(RAW_CHOICES + list(raw_choices))
        self._make_consts(*raw_choices)
        if name != "CHOICES":
            # for retrocompatibility
            # we make a subset with new choices
            constants_for_subset = []
            for choice in raw_choices:
                const, value, string = choice
                constants_for_subset.append(const)
            self.add_subset(name, constants_for_subset)

    def add_subset(self, name, constants):
        if hasattr(self, name):
            raise ValueError("Cannot use %s as a subset name."
                             "It's already an attribute." % name)

        subset = Choices(parent=self, CONSTS=constants)
        setattr(self, name, subset)

        # For retrocompatibility
        setattr(self, '%s_DICT' % name, getattr(subset, "CHOICES_DICT"))
        setattr(self, 'REVERTED_%s_DICT' % name,
                getattr(subset, "REVERTED_CHOICES_DICT"))

    @property
    def RAW_CHOICES(self):
        if self._RAW_CHOICES is None:
            if self.parent:
                self._RAW_CHOICES = tuple((c, k, v) for c, k, v
                                          in self.parent.RAW_CHOICES
                                          if c in self._CONSTS)
            else:
                raise ValueError("Implementation problem : first "
                                 "ancestor should have a _RAW_CHOICES")
        return self._RAW_CHOICES

    @property
    def CHOICES(self):
        """
        Tuple of tuples (value, display_value).
        """
        if self._CHOICES is None:
            self._CHOICES = tuple((k, v) for c, k, v in self.RAW_CHOICES
                                  if c in self._CONSTS)
        return self._CHOICES

    @property
    def CHOICES_DICT(self):
        if self._CHOICES_DICT is None:
            self._CHOICES_DICT = {}
            for c, k, v in self.RAW_CHOICES:
                if c in self._CONSTS:
                    self._CHOICES_DICT[k] = v
        return self._CHOICES_DICT

    @property
    def REVERTED_CHOICES_DICT(self):
        """
        Dict {"display_value": "value"}
        """
        # FIXME: rename in a more friendly name, like STRING_TO_VALUE?
        if self._REVERTED_CHOICES_DICT is None:
            self._REVERTED_CHOICES_DICT = {}
            for c, k, v in self.RAW_CHOICES:
                if c in self._CONSTS:
                    self._REVERTED_CHOICES_DICT[v] = k
        return self._REVERTED_CHOICES_DICT

    @property
    def VALUE_TO_CONST(self):
        """
        Dict {"value": "const"}
        """
        if self._VALUE_TO_CONST is None:
            self._VALUE_TO_CONST = {}
            for c, k, v in self.RAW_CHOICES:
                if c in self._CONSTS:
                    self._VALUE_TO_CONST[k] = c
        return self._VALUE_TO_CONST

    @property
    def CONST_CHOICES(self):
        """
        Tuple of tuples (constant, display_value).
        """
        if self._CONST_CHOICES is None:
            self._CONST_CHOICES = tuple((c, v) for c, k, v in self.RAW_CHOICES
                                        if c in self._CONSTS)
        return self._CONST_CHOICES

    def __contains__(self, item):
        """
        Make smarter to check if a value is valid for a Choices.
        """
        return item in self.CHOICES_DICT

    def __iter__(self):
        return self.CHOICES.__iter__()

    def __eq__(self, other):
        return other == self.CHOICES

    def __ne__(self, other):
        return other != self.CHOICES

    def __len__(self):
        return self.CHOICES.__len__()

    def __add__(self, item):
        """
        Needed to make MY_CHOICES + OTHER_CHOICE
        """
        if not isinstance(item, (Choices, tuple)):
            raise ValueError("This operand could only by evaluated "
                             "with Choices or tuple instances. "
                             "Got %s instead." % type(item))
        return self.CHOICES + tuple(item)

    def __repr__(self):
        return self.CHOICES.__repr__()
