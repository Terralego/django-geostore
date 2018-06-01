import json
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.gis.db import models
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.gis.geos.point import Point
from django.contrib.postgres.fields import JSONField
from django.core.serializers import serialize
from django.db import transaction
from django.db.models import Manager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from mercantile import tiles

from .fields import DateFieldYearLess
from .helpers import ChunkIterator
from .managers import FeatureQuerySet, TerraUserManager
from .tiles.helpers import VectorTile


class Layer(models.Model):
    name = models.CharField(max_length=256)
    group = models.CharField(max_length=255, default="__nogroup__")
    schema = JSONField(default=dict, blank=True)

    def from_csv_dictreader(self, reader, pk_properties, init=False,
                            chunk_size=1000, fast=False):
        """Import (create or update) features from csv.DictReader object
        :param reader: csv.DictReader object
        :param pk_properties: keys of row that is used to identify unicity
        :param init: allow to speed up import if there is only new Feature's
                    (no updates)
        :param chunk_size: only used if init=True, control the size of
                           bulk_create
        """
        # rl = list(reader)
        chunks = ChunkIterator(reader, chunk_size)
        if init:
            for chunk in chunks:
                entries = [
                    Feature(
                        geom=Point(),
                        properties=row,
                        layer=self,
                    )
                    for row in chunk
                ]
                Feature.objects.bulk_create(entries)
        else:
            for chunk in chunks:
                sp = None
                if fast:
                    sp = transaction.savepoint()
                for row in chunk:
                    Feature.objects.update_or_create(
                        defaults={
                            'geom': Point(),
                            'properties': row,
                            'layer': self,
                        },
                        layer=self,
                        **{f'properties__{p}': row.get(p, '')
                            for p in pk_properties}
                    )
                if sp:
                    transaction.savepoint_commit(sp)

    def from_geojson(self, geojson_data, from_date, to_date, update=False):
        """
        Import geojson raw data in a layer
        Args:
            geojson_data(str): must be raw text json data
        """
        geojson = json.loads(geojson_data)
        if update:
            self.features.all().delete()
        for feature in geojson.get('features', []):
            Feature.objects.create(
                layer=self,
                properties=feature.get('properties', {}),
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
    properties = JSONField()
    layer = models.ForeignKey(Layer,
                              on_delete=models.PROTECT,
                              related_name='features')
    from_date = DateFieldYearLess(help_text="Layer validity period start",
                                  default='01-01')
    to_date = DateFieldYearLess(help_text="Layer validity period end",
                                default='12-31')

    objects = Manager.from_queryset(FeatureQuerySet)()

    def clean_cache(self):
        vtile = VectorTile(self.layer)
        vtile.clean_tiles(self.get_intersected_tiles())

    def get_intersected_tiles(self):
        return [(tile.x, tile.y, tile.z)
                for tile in tiles(*self.get_bounding_box(),
                                  range(settings.MAX_TILE_ZOOM + 1))]

    def get_bounding_box(self):
        return self.geom.extent

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


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
