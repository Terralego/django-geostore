import json
import logging
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.gis.db import models
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.postgres.fields import JSONField
from django.core.serializers import serialize
from django.db import transaction
from django.db.models import Manager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from mercantile import tiles

from .fields import DateFieldYearLess
from .helpers import ChunkIterator, GeometryDefiner
from .managers import FeatureQuerySet, TerraUserManager
from .tiles.helpers import VectorTile

logger = logging.getLogger(__name__)


class Layer(models.Model):
    name = models.CharField(max_length=256)
    group = models.CharField(max_length=255, default="__nogroup__")
    schema = JSONField(default=dict, blank=True)

    def _initial_import_from_csv(self, chunks, geometry_columns=None):
        for chunk in chunks:
            entries = []
            for row in chunk:
                geometry = GeometryDefiner.get_geometry(geometry_columns, row)
                if geometry is None:
                    logger.warning(f'geometry error, row skipped : {row}')
                    continue
                entries.append(
                    Feature(
                        geom=geometry,
                        properties=row,
                        layer=self,
                    )
                )
            Feature.objects.bulk_create(entries)

    def _complementary_import_from_csv(self, chunks, pk_properties,
                                       fast=False, geometry_columns=None):
        for chunk in chunks:
            sp = None
            if fast:
                sp = transaction.savepoint()
            for row in chunk:
                geometry = GeometryDefiner.get_geometry(geometry_columns, row)
                filter_kwargs = {f'properties__{p}': row.get(p, '')
                                 for p in pk_properties}
                filter_kwargs['layer'] = self
                if geometry is not None:
                    Feature.objects.update_or_create(
                        defaults={
                            'geom': geometry,
                            'properties': row,
                            'layer': self,
                        },
                        **filter_kwargs
                    )
                else:
                    try:
                        Feature.objects.filter(**filter_kwargs).update(
                            **{'properties': row})
                    except Feature.DoesNotExist:
                        logger.warning('feature does not exist, '
                                       'empty geometry, '
                                       f'row skipped : {row}')
                        continue
            if sp:
                transaction.savepoint_commit(sp)

    def from_csv_dictreader(self, reader, pk_properties, init=False,
                            chunk_size=1000, fast=False,
                            geometry_columns=None):
        """Import (create or update) features from csv.DictReader object
        :param reader: csv.DictReader object
        :param pk_properties: keys of row that is used to identify unicity
        :param init: allow to speed up import if there is only new Feature's
                    (no updates)
        :param chunk_size: only used if init=True, control the size of
                           bulk_create
        :param geometry_columns: name of geometry columns
        """
        chunks = ChunkIterator(reader, chunk_size)
        if init:
            self._initial_import_from_csv(chunks, geometry_columns)
        else:
            self._complementary_import_from_csv(chunks, pk_properties, fast,
                                                geometry_columns)

    def from_geojson(self, geojson_data, from_date, to_date, id_field=None,
                     update=False):
        """
        Import geojson raw data in a layer
        Args:
            geojson_data(str): must be raw text json data
        """
        geojson = json.loads(geojson_data)
        if update:
            self.features.all().delete()
        for feature in geojson.get('features', []):
            properties = feature.get('properties', {})
            identifier = properties.get(id_field, uuid.uuid4())
            Feature.objects.create(
                layer=self,
                identifier=identifier,
                properties=properties,
                geom=GEOSGeometry(json.dumps(feature.get('geometry'))),
                from_date=from_date,
                to_date=to_date
            )

    def to_geojson(self):
        return json.loads(serialize('geojson',
                                    self.features.all(),
                                    fields=('properties',),
                                    geometry_field='geom',
                                    properties_field='properties'))


class Feature(models.Model):
    geom = models.GeometryField()
    identifier = models.CharField(max_length=255,
                                  blank=False,
                                  null=False,
                                  default=uuid.uuid4)
    properties = JSONField()
    layer = models.ForeignKey(Layer,
                              on_delete=models.PROTECT,
                              related_name='features')
    from_date = DateFieldYearLess(help_text="Layer validity period start",
                                  default='01-01')
    to_date = DateFieldYearLess(help_text="Layer validity period end",
                                default='12-31')

    objects = Manager.from_queryset(FeatureQuerySet)()

    def clean_vect_tile_cache(self):
        vtile = VectorTile(self.layer)
        vtile.clean_tiles(self.get_intersected_tiles())

    def get_intersected_tiles(self):
        zoom_range = range(settings.MIN_TILE_ZOOM, settings.MAX_TILE_ZOOM)
        try:
            return [(tile.x, tile.y, tile.z)
                    for tile in tiles(*self.get_bounding_box(), zoom_range)]
        except ValueError:
            # TODO find why a ValueError is raised with some Point() geometries
            return []

    def get_bounding_box(self):
        return self.geom.extent

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.clean_vect_tile_cache()


class LayerRelation(models.Model):
    origin = models.ForeignKey(Layer,
                               on_delete=models.PROTECT,
                               related_name='relations_as_origin')
    destination = models.ForeignKey(Layer,
                                    on_delete=models.PROTECT,
                                    related_name='relations_as_destination')
    schema = JSONField(default=dict, blank=True)


class FeatureRelation(models.Model):
    origin = models.ForeignKey(Feature,
                               on_delete=models.PROTECT,
                               related_name='relations_as_origin')
    destination = models.ForeignKey(Feature,
                                    on_delete=models.PROTECT,
                                    related_name='relations_as_destination')
    properties = JSONField(default=dict, blank=True)


class TerraUser(AbstractBaseUser, PermissionsMixin):
    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    uuid = models.UUIDField(_('unique identifier'),
                            default=uuid.uuid4,
                            editable=False,
                            unique=True)
    email = models.EmailField(_('email address'), blank=True, unique=True)
    properties = JSONField(default=dict, blank=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user '
                    'can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = TerraUserManager()
